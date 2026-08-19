#!/usr/bin/env python3
"""
Voice Notes Bot - Web Application
Aplikacja webowa do przeglądania notatek głosowych
"""

import os
import logging
from datetime import datetime
import json
import hashlib
import hmac
import threading
import uuid
from functools import wraps

from flask import Flask, render_template, request, Response, session, redirect, url_for, jsonify
from dotenv import load_dotenv

# Import modułów bota
from database import Database

# Konfiguracja
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('WEB_SECRET_KEY', 'dev-secret-key-change-in-production')

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicjalizacja bazy danych
db = Database()

# Telegram Bot Token (do pobierania zdjęć)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_BOT_USERNAME = 'Lichtus_notes_bot'

# Przechowywanie kodów weryfikacyjnych (user_id -> {code, timestamp, user_data})
login_codes = {}


# ============================================
# TELEGRAM LOGIN - AUTHENTICATION
# ============================================

def verify_telegram_auth(auth_data):
    """
    Weryfikuje autentyczność danych z Telegram Login Widget
    Zgodnie z: https://core.telegram.org/widgets/login#checking-authorization
    """
    check_hash = auth_data.get('hash')
    if not check_hash:
        return False

    # Usuń hash z danych
    auth_data_copy = {k: v for k, v in auth_data.items() if k != 'hash'}

    # Sortuj klucze i utwórz string do weryfikacji
    data_check_arr = [f"{k}={v}" for k, v in sorted(auth_data_copy.items())]
    data_check_string = '\n'.join(data_check_arr)

    # Oblicz hash
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Porównaj hash
    if calculated_hash != check_hash:
        logger.warning("Invalid Telegram auth hash")
        return False

    # Sprawdź czy dane nie są starsze niż 24h
    auth_date = int(auth_data.get('auth_date', 0))
    current_timestamp = int(datetime.now().timestamp())

    if current_timestamp - auth_date > 86400:  # 24 godziny
        logger.warning("Telegram auth data too old")
        return False

    return True


def biezacy_user_id():
    """
    ID zalogowanego użytkownika. Widoki używające tej funkcji są za
    @login_required, więc sesja na pewno istnieje.
    """
    return int(session['telegram_user_id'])


def login_required(f):
    """Dekorator wymagający zalogowania przez Telegram"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'telegram_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def generate_login_code():
    """Generuje 6-cyfrowy kod weryfikacyjny"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def store_login_code(user_id, code, user_data):
    """Przechowuje kod weryfikacyjny dla użytkownika"""
    login_codes[user_id] = {
        'code': code,
        'timestamp': datetime.now(),
        'user_data': user_data
    }
    logger.info(f"Stored login code for user {user_id}")


def verify_login_code(user_id, code):
    """Weryfikuje kod weryfikacyjny"""
    if user_id not in login_codes:
        logger.warning(f"No login code found for user {user_id}")
        return None

    stored = login_codes[user_id]

    # Sprawdź czy kod nie wygasł (5 minut)
    if (datetime.now() - stored['timestamp']).seconds > 300:
        logger.warning(f"Login code expired for user {user_id}")
        del login_codes[user_id]
        return None

    # Sprawdź czy kod się zgadza
    if stored['code'] != code:
        logger.warning(f"Invalid login code for user {user_id}")
        return None

    # Usuń użyty kod
    user_data = stored['user_data']
    del login_codes[user_id]
    logger.info(f"Login code verified for user {user_id}")

    return user_data


# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/login')
def login():
    """Strona logowania przez Telegram"""
    # Jeśli użytkownik już zalogowany, przekieruj do notatek
    if 'telegram_user_id' in session:
        return redirect(url_for('notes_list'))

    return render_template('login.html',
                         bot_username=TELEGRAM_BOT_USERNAME,
                         auth_url=url_for('telegram_auth', _external=True))


@app.route('/auth/telegram')
def telegram_auth():
    """Callback po zalogowaniu przez Telegram Widget"""
    # Pobierz wszystkie parametry z query string
    auth_data = request.args.to_dict()

    # Weryfikuj autentyczność danych
    if not verify_telegram_auth(auth_data):
        logger.error("Telegram authentication failed")
        return "Authentication failed. Invalid or expired data.", 403

    # Zapisz dane użytkownika w sesji
    session['telegram_user_id'] = int(auth_data.get('id'))
    session['first_name'] = auth_data.get('first_name', '')
    session['last_name'] = auth_data.get('last_name', '')
    session['username'] = auth_data.get('username', '')
    session['photo_url'] = auth_data.get('photo_url', '')

    logger.info(f"User logged in: {session['first_name']} (ID: {session['telegram_user_id']})")

    # Przekieruj do strony z notatkami
    return redirect(url_for('notes_list'))


@app.route('/logout')
def logout():
    """Wylogowanie użytkownika"""
    user_name = session.get('first_name', 'Unknown')
    session.clear()
    logger.info(f"User logged out: {user_name}")
    return redirect(url_for('login'))


@app.route('/api/store-code', methods=['POST'])
def api_store_code():
    """
    API endpoint dla bota do przechowania wygenerowanego kodu
    Bot wywołuje ten endpoint po wygenerowaniu kodu
    """
    # Bez tego każdy, kto dosięgnie tego portu, podłożyłby sobie kod logowania
    # na dowolne user_id i wszedł przez /verify-code. Bot zna WEB_SECRET_KEY
    # z tego samego .env, więc nie trzeba nowej zmiennej.
    sekret = os.getenv('WEB_SECRET_KEY')
    if not sekret or request.headers.get('X-Bot-Secret') != sekret:
        logger.warning("Odrzucono /api/store-code — brak albo zły X-Bot-Secret")
        return {'success': False, 'error': 'Unauthorized'}, 401

    try:
        data = request.get_json()

        # Weryfikacja danych
        required_fields = ['user_id', 'code', 'first_name']
        if not all(field in data for field in required_fields):
            return {'success': False, 'error': 'Missing required fields'}, 400

        # Przechowaj kod
        user_data = {
            'telegram_user_id': data['user_id'],
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'username': data.get('username', ''),
        }

        store_login_code(data['user_id'], data['code'], user_data)

        return {'success': True}, 200

    except Exception as e:
        logger.error(f"Error storing code: {e}")
        return {'success': False, 'error': str(e)}, 500


@app.route('/verify-code', methods=['POST'])
def verify_code_route():
    """Weryfikuje kod wpisany przez użytkownika"""
    try:
        user_id = request.form.get('user_id')
        code = request.form.get('code')

        if not user_id or not code:
            return render_template('login.html',
                                 bot_username=TELEGRAM_BOT_USERNAME,
                                 auth_url=url_for('telegram_auth', _external=True),
                                 error="Podaj ID użytkownika i kod weryfikacyjny")

        # Weryfikuj kod
        user_data = verify_login_code(int(user_id), code)

        if not user_data:
            return render_template('login.html',
                                 bot_username=TELEGRAM_BOT_USERNAME,
                                 auth_url=url_for('telegram_auth', _external=True),
                                 error="Nieprawidłowy lub wygasły kod")

        # Zaloguj użytkownika
        session['telegram_user_id'] = user_data['telegram_user_id']
        session['first_name'] = user_data['first_name']
        session['last_name'] = user_data['last_name']
        session['username'] = user_data['username']

        logger.info(f"User logged in via code: {session['first_name']} (ID: {session['telegram_user_id']})")

        return redirect(url_for('notes_list'))

    except Exception as e:
        logger.error(f"Error verifying code: {e}")
        return render_template('login.html',
                             bot_username=TELEGRAM_BOT_USERNAME,
                             auth_url=url_for('telegram_auth', _external=True),
                             error="Błąd podczas weryfikacji kodu")


# ============================================
# NOTES ROUTES
# ============================================

@app.route('/')
@login_required
def index():
    """Strona główna - przekierowanie do notatek"""
    return redirect(url_for('notes_list'))


@app.route('/notes')
@login_required
def notes_list():
    """Lista wszystkich notatek z wyszukiwaniem, filtrowaniem i sortowaniem"""
    from database import Notatka, Zadanie
    from sqlalchemy import func, or_
    from datetime import timedelta

    # Pobierz ID użytkownika z .env (tylko jeden użytkownik)
    telegram_user_id = biezacy_user_id()

    # Pobierz parametry z URL
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '', type=str).strip()
    date_filter = request.args.get('date_filter', 'all', type=str)
    tasks_filter = request.args.get('tasks_filter', 'all', type=str)
    category_filter = request.args.get('category_filter', 'all', type=str)
    sort_by = request.args.get('sort', 'date_desc', type=str)

    # Buduj zapytanie - TYLKO aktywne notatki zalogowanego użytkownika (bez usuniętych)
    query = db.session.query(Notatka).filter(
        Notatka.telegram_user_id == telegram_user_id,
        Notatka.deleted_at.is_(None)
    )

    # Wyszukiwanie
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Notatka.temat.ilike(search_pattern),
                Notatka.opis.ilike(search_pattern),
                Notatka.transkrypcja.ilike(search_pattern)
            )
        )

    # Filtrowanie po dacie
    if date_filter != 'all':
        now = datetime.now()
        if date_filter == '7days':
            cutoff_date = now - timedelta(days=7)
            query = query.filter(Notatka.data_utworzenia >= cutoff_date)
        elif date_filter == '30days':
            cutoff_date = now - timedelta(days=30)
            query = query.filter(Notatka.data_utworzenia >= cutoff_date)
        elif date_filter == '90days':
            cutoff_date = now - timedelta(days=90)
            query = query.filter(Notatka.data_utworzenia >= cutoff_date)

    # Filtrowanie po zadaniach
    if tasks_filter == 'with_tasks':
        # Notatki z przynajmniej jednym zadaniem
        query = query.join(Zadanie, Notatka.id == Zadanie.notatka_id)
    elif tasks_filter == 'without_tasks':
        # Notatki bez zadań
        query = query.outerjoin(Zadanie, Notatka.id == Zadanie.notatka_id).group_by(Notatka.id).having(func.count(Zadanie.id) == 0)
    elif tasks_filter == 'with_incomplete':
        # Notatki z niewykonanymi zadaniami
        query = query.join(Zadanie, Notatka.id == Zadanie.notatka_id).filter(Zadanie.wykonane == False)

    # Grupuj po notatce (dla JOIN z zadaniami)
    if tasks_filter in ['with_tasks', 'with_incomplete']:
        query = query.group_by(Notatka.id)

    # Filtrowanie po kategorii
    if category_filter != 'all':
        query = query.filter(Notatka.kategoria == category_filter)

    # Sortowanie
    if sort_by == 'date_desc':
        query = query.order_by(Notatka.data_utworzenia.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Notatka.data_utworzenia.asc())
    elif sort_by == 'title_asc':
        query = query.order_by(Notatka.temat.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Notatka.temat.desc())
    elif sort_by in ['tasks_desc', 'tasks_asc']:
        # Dla sortowania po zadaniach, jeśli nie filtrujemy już po zadaniach
        if tasks_filter not in ['with_tasks', 'without_tasks', 'with_incomplete']:
            # Musimy zrobić LEFT JOIN i GROUP BY
            query = query.outerjoin(Zadanie, Notatka.id == Zadanie.notatka_id)
            query = query.group_by(Notatka.id)

        # Sortuj po liczbie zadań
        if sort_by == 'tasks_desc':
            query = query.order_by(func.count(Zadanie.id).desc())
        else:
            query = query.order_by(func.count(Zadanie.id).asc())

    # Paginacja
    total_notes = query.count()
    total_pages = (total_notes + per_page - 1) // per_page

    # Pobierz notatki
    notes = query.offset((page - 1) * per_page).limit(per_page).all()

    # Przygotuj dane notatek
    notes_data = []
    for note in notes:
        zadania_count = len(note.zadania) if note.zadania else 0
        photo_count = len(json.loads(note.photo_file_ids)) if note.photo_file_ids else 0

        # Sprawdź czy notatka była edytowana
        is_edited = '✏️ *Edytowano:*' in note.opis if note.opis else False
        edit_date = None
        if is_edited:
            # Ekstrahuj datę edycji z opisu
            import re
            match = re.search(r'✏️ \*Edytowano:\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', note.opis)
            if match:
                edit_date = match.group(1)

        notes_data.append({
            'id': note.id,
            'temat': note.temat,
            'opis': note.opis[:200] + '...' if len(note.opis) > 200 else note.opis,
            'data_utworzenia': note.data_utworzenia,
            'zadania_count': zadania_count,
            'photo_count': photo_count,
            'kategoria': note.kategoria,
            'is_edited': is_edited,
            'edit_date': edit_date
        })

    return render_template('notes_list.html',
                         notes=notes_data,
                         page=page,
                         total_pages=total_pages,
                         total_notes=total_notes,
                         search=search,
                         date_filter=date_filter,
                         tasks_filter=tasks_filter,
                         category_filter=category_filter,
                         sort_by=sort_by,
                         user=session)


@app.route('/notes/<int:note_id>')
@login_required
def note_detail(note_id):
    """Szczegóły pojedynczej notatki"""
    from database import Notatka

    # Pobierz ID użytkownika z .env
    telegram_user_id = biezacy_user_id()

    # Pobierz notatkę TYLKO jeśli należy do zalogowanego użytkownika
    note = db.session.query(Notatka).filter_by(
        id=note_id,
        telegram_user_id=telegram_user_id
    ).first()

    if not note:
        return "Notatka nie znaleziona lub nie masz do niej dostępu", 404

    # Przygotuj dane - note.zadania to relacja ORM do obiektów Zadanie
    photo_file_ids = json.loads(note.photo_file_ids) if note.photo_file_ids else []

    # Parsuj dane analizy głębokiej jeśli istnieją
    analiza = None
    if note.czy_analizowane:
        analiza = {
            'tytul': note.analiza_tytul,
            'uczestnicy': json.loads(note.analiza_uczestnicy) if note.analiza_uczestnicy else [],
            'sekcje': json.loads(note.analiza_sekcje) if note.analiza_sekcje else [],
            'ustalenia': json.loads(note.analiza_ustalenia) if note.analiza_ustalenia else [],
            'daty_chronologicznie': json.loads(note.analiza_daty_chronologicznie) if note.analiza_daty_chronologicznie else [],
            'podsumowanie_dat': note.analiza_podsumowanie_dat
        }

    # Sprawdź czy notatka była edytowana
    is_edited = '✏️ *Edytowano:*' in note.opis if note.opis else False
    edit_date = None
    if is_edited:
        # Ekstrahuj datę edycji z opisu
        import re
        match = re.search(r'✏️ \*Edytowano:\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', note.opis)
        if match:
            edit_date = match.group(1)

    # Oblicz łączną liczbę tokenów
    tokens_total = None
    if note.tokens_input or note.tokens_output or note.tokens_embedding:
        tokens_total = (note.tokens_input or 0) + (note.tokens_output or 0) + (note.tokens_embedding or 0)

    note_data = {
        'id': note.id,
        'temat': note.temat,
        'opis': note.opis,
        'transkrypcja': note.transkrypcja,
        'data_utworzenia': note.data_utworzenia,
        'zadania': note.zadania,  # Przekazujemy pełne obiekty Zadanie
        'photo_file_ids': photo_file_ids,
        'has_photos': len(photo_file_ids) > 0,
        'kategoria': note.kategoria,
        'is_edited': is_edited,
        'edit_date': edit_date,
        'czy_analizowane': note.czy_analizowane,  # Czy przeprowadzono dogłębną analizę
        # Dane kosztów AI
        'cost_total_usd': note.cost_total_usd,
        'tokens_total': tokens_total,
        'processing_time': note.processing_time,
        'auto_category_confidence': note.auto_category_confidence
    }

    return render_template('note_detail.html', note=note_data, analiza=analiza, user=session)


@app.route('/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_note(note_id):
    """Usuwa notatkę (soft delete)"""
    from database import Database

    telegram_user_id = biezacy_user_id()
    db_handler = Database()

    # Soft delete notatki
    success = db_handler.soft_delete_notatka(note_id, telegram_user_id)

    if success:
        return redirect(url_for('notes_list'))
    else:
        return "Notatka nie znaleziona lub nie masz do niej dostępu", 404


@app.route('/notes/<int:note_id>/update-category', methods=['POST'])
@login_required
def update_note_category(note_id):
    """Aktualizuje kategorię notatki"""
    from database import Database

    telegram_user_id = biezacy_user_id()
    new_category = request.form.get('kategoria')

    # Walidacja kategorii
    if new_category not in ['Praca', 'Dom', 'Inne']:
        return "Nieprawidłowa kategoria", 400

    db_handler = Database()
    note = db_handler.update_notatka(
        note_id,
        telegram_user_id,
        kategoria=new_category
    )

    if note:
        return redirect(url_for('note_detail', note_id=note_id))
    else:
        return "Notatka nie znaleziona lub nie masz do niej dostępu", 404


@app.route('/tasks')
@login_required
def tasks_list():
    """Lista wszystkich zadań użytkownika"""
    from database import Notatka, Zadanie

    telegram_user_id = biezacy_user_id()

    # Pobierz parametry filtrowania
    status_filter = request.args.get('status', 'all', type=str)
    sort_by = request.args.get('sort', 'note_date_desc', type=str)

    # Buduj zapytanie - zadania z aktywnych notatek użytkownika
    query = db.session.query(Zadanie)\
        .join(Notatka)\
        .filter(
            Notatka.telegram_user_id == telegram_user_id,
            Notatka.deleted_at.is_(None)
        )

    # Filtrowanie po statusie
    if status_filter == 'completed':
        query = query.filter(Zadanie.wykonane == True)
    elif status_filter == 'pending':
        query = query.filter(Zadanie.wykonane == False)

    # Sortowanie
    if sort_by == 'note_date_desc':
        query = query.order_by(Notatka.data_utworzenia.desc())
    elif sort_by == 'note_date_asc':
        query = query.order_by(Notatka.data_utworzenia.asc())
    elif sort_by == 'completion_date':
        query = query.order_by(Zadanie.data_wykonania.desc().nullslast())
    elif sort_by == 'task_id':
        query = query.order_by(Zadanie.id.asc())

    # Pobierz wszystkie zadania
    tasks = query.all()

    # Przygotuj dane dla szablonu
    tasks_data = []
    for task in tasks:
        tasks_data.append({
            'id': task.id,
            'zadanie': task.zadanie,
            'wykonane': task.wykonane,
            'data_wykonania': task.data_wykonania,
            'notatka_id': task.notatka.id,
            'notatka_temat': task.notatka.temat,
            'notatka_data': task.notatka.data_utworzenia,
            'notatka_kategoria': task.notatka.kategoria
        })

    # Statystyki
    total_tasks = len(tasks_data)
    completed_tasks = sum(1 for t in tasks_data if t['wykonane'])
    pending_tasks = total_tasks - completed_tasks

    return render_template('tasks_list.html',
                         tasks=tasks_data,
                         status_filter=status_filter,
                         sort_by=sort_by,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         pending_tasks=pending_tasks,
                         user=session)


@app.route('/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    """Przełącza status zadania (wykonane/niewykonane)"""
    from database import Zadanie, Notatka

    telegram_user_id = biezacy_user_id()

    # Znajdź zadanie i sprawdź czy należy do użytkownika
    task = db.session.query(Zadanie)\
        .join(Notatka)\
        .filter(
            Zadanie.id == task_id,
            Notatka.telegram_user_id == telegram_user_id,
            Notatka.deleted_at.is_(None)
        ).first()

    if not task:
        return jsonify({'error': 'Zadanie nie znalezione'}), 404

    # Przełącz status
    task.wykonane = not task.wykonane
    task.data_wykonania = datetime.now() if task.wykonane else None
    db.session.commit()

    # Zwróć JSON z danymi zadania (dla AJAX)
    return jsonify({
        'success': True,
        'task_id': task.id,
        'wykonane': task.wykonane,
        'data_wykonania': task.data_wykonania.strftime('%Y-%m-%d %H:%M') if task.data_wykonania else None
    })


def generate_email_html(note, base_url=None):
    """Generuje pięknie sformatowany HTML dla emaila"""
    # Formatuj zadania
    zadania_html = ""
    if note['zadania']:
        zadania_html = "<div class='tasks'>"
        for i, zadanie in enumerate(note['zadania'], 1):
            zadania_html += f"<div class='task'>☐ {zadanie}</div>"
        zadania_html += "</div>"
    else:
        zadania_html = "<p><em>Brak zadań</em></p>"

    # Formatuj zdjęcia
    photos_html = ""
    if note.get('photo_file_ids') and base_url:
        photos_html = """
        <div class="section">
            <h2>📷 Zdjęcia</h2>
            <div class="photos">"""
        for i in range(len(note['photo_file_ids'])):
            photo_url = f"{base_url}notes/{note['id']}/photo/{i}"
            photos_html += f"""
                <img src="{photo_url}" alt="Zdjęcie {i+1}"
                     style="max-width: 100%; height: auto; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">"""
        photos_html += """
            </div>
        </div>"""

    # Formatuj datę
    data_str = note['data_utworzenia'].strftime("%d.%m.%Y %H:%M")

    # Informacja o edycji
    edit_info = ""
    if note.get('is_edited') and note.get('edit_date'):
        edit_info = f"<p class='edit-info'>✏️ Ostatnia edycja: {note['edit_date']}</p>"

    # Szablon HTML
    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{note['temat']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px 10px 0 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .header .date {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .content {{
            background: white;
            padding: 30px;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section {{
            margin: 25px 0;
            padding: 20px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 5px;
        }}
        .section h2 {{
            margin: 0 0 15px 0;
            color: #667eea;
            font-size: 20px;
        }}
        .section p {{
            margin: 0;
            white-space: pre-wrap;
        }}
        .tasks {{
            margin-top: 15px;
        }}
        .task {{
            background: #fff3cd;
            padding: 12px 15px;
            margin: 8px 0;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
            font-size: 15px;
        }}
        .edit-info {{
            color: #6c757d;
            font-size: 14px;
            font-style: italic;
            margin-top: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #6c757d;
            font-size: 12px;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📝 {note['temat']}</h1>
        <div class="date">📅 {data_str}</div>
        {edit_info}
    </div>

    <div class="content">
        <div class="section">
            <h2>📌 Opis</h2>
            <p>{note['opis']}</p>
        </div>

        <div class="section">
            <h2>📋 Zadania</h2>
            {zadania_html}
        </div>

        {photos_html}
    </div>

    <div class="footer">
        Wygenerowano przez Voice Notes Bot<br>
        Notatka #{note['id']}
    </div>
</body>
</html>"""

    return html


@app.route('/notes/<int:note_id>/email')
@login_required
def prepare_email(note_id):
    """Przygotuj mailto link z notatką"""
    import urllib.parse
    from database import Notatka

    # Pobierz ID użytkownika z .env
    telegram_user_id = biezacy_user_id()

    # Pobierz notatkę TYLKO jeśli należy do zalogowanego użytkownika
    note = db.session.query(Notatka).filter_by(
        id=note_id,
        telegram_user_id=telegram_user_id
    ).first()

    if not note:
        return "Notatka nie znaleziona lub nie masz do niej dostępu", 404

    # Przygotuj dane notatki
    zadania_list = [z.zadanie for z in note.zadania] if note.zadania else []

    # Sprawdź czy notatka była edytowana
    is_edited = '✏️ *Edytowano:*' in note.opis if note.opis else False
    edit_date = None
    if is_edited:
        import re
        match = re.search(r'✏️ \*Edytowano:\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', note.opis)
        if match:
            edit_date = match.group(1)

    # Pobierz photo_file_ids
    photo_file_ids = json.loads(note.photo_file_ids) if note.photo_file_ids else []

    note_data = {
        'id': note.id,
        'temat': note.temat,
        'opis': note.opis,
        'data_utworzenia': note.data_utworzenia,
        'zadania': zadania_list,
        'photo_file_ids': photo_file_ids,
        'is_edited': is_edited,
        'edit_date': edit_date
    }

    # Generuj HTML z URL bazowym dla zdjęć
    base_url = request.host_url  # np. "http://localhost:5000/"
    html_body = generate_email_html(note_data, base_url)

    # Przygotuj mailto link
    subject = f"Notatka: {note.temat}"

    # Encode HTML dla mailto (niektóre klienty email nie wspierają HTML w mailto body)
    # Więc dodajemy też wersję tekstową
    text_body = f"""
Notatka #{note.id}: {note.temat}
Data: {note.data_utworzenia.strftime('%d.%m.%Y %H:%M')}
{'Edytowano: ' + edit_date if edit_date else ''}

OPIS:
{note.opis}

ZADANIA:
"""
    if zadania_list:
        for i, zadanie in enumerate(zadania_list, 1):
            text_body += f"{i}. {zadanie}\n"
    else:
        text_body += "Brak zadań\n"

    text_body += "\n---\nWygenerowano przez Voice Notes Bot"

    # Redirect do strony z mailto linkiem (bo niektóre przeglądarki blokują automatyczne mailto)
    return render_template('email_redirect.html',
                         subject=urllib.parse.quote(subject),
                         body=urllib.parse.quote(text_body),
                         html_body=html_body,
                         note_id=note_id)


@app.route('/notes/<int:note_id>/photo/<int:photo_index>')
@login_required
def get_photo(note_id, photo_index):
    """Pobierz zdjęcie z Telegram i wyślij jako odpowiedź"""
    import requests
    from database import Notatka

    # Pobierz ID użytkownika z .env
    telegram_user_id = biezacy_user_id()

    # Pobierz notatkę TYLKO jeśli należy do zalogowanego użytkownika
    note = db.session.query(Notatka).filter_by(
        id=note_id,
        telegram_user_id=telegram_user_id
    ).first()

    if not note or not note.photo_file_ids:
        return "Zdjęcie nie znalezione lub nie masz do niego dostępu", 404

    photo_file_ids = json.loads(note.photo_file_ids)

    if photo_index < 0 or photo_index >= len(photo_file_ids):
        return "Nieprawidłowy indeks zdjęcia", 404

    file_id = photo_file_ids[photo_index]

    try:
        # Pobierz informacje o pliku z Telegram
        file_response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
            params={'file_id': file_id}
        )
        file_data = file_response.json()

        if not file_data.get('ok'):
            logger.error(f"Błąd pobierania pliku z Telegram: {file_data}")
            return "Błąd pobierania zdjęcia", 500

        file_path = file_data['result']['file_path']

        # Pobierz sam plik
        photo_response = requests.get(
            f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        )

        if photo_response.status_code != 200:
            return "Błąd pobierania zdjęcia", 500

        # Zwróć zdjęcie jako odpowiedź
        return Response(
            photo_response.content,
            mimetype='image/jpeg',
            headers={'Cache-Control': 'public, max-age=86400'}
        )

    except Exception as e:
        logger.error(f"Błąd pobierania zdjęcia: {e}")
        return "Błąd serwera", 500


# ============================================
# WGRYWANIE PLIKÓW AUDIO
# ============================================

# Formaty przyjmowane zarówno przez AssemblyAI, jak i przez Whisper.
DOZWOLONE_FORMATY = {'.mp3', '.mp4', '.m4a', '.wav', '.ogg', '.oga',
                     '.webm', '.flac', '.mpeg', '.mpga'}

# Limit nie wynika z Telegrama (ten kończy się na 20 MB przy pobieraniu przez
# bota) — tutaj plik idzie prosto z przeglądarki, więc godzinne spotkanie
# przechodzi bez przekodowywania.
MAX_ROZMIAR_MB = 100
app.config['MAX_CONTENT_LENGTH'] = MAX_ROZMIAR_MB * 1024 * 1024

# Stan zadań w pamięci procesu — jak kody logowania, ginie przy restarcie.
zadania_uploadu = {}


def przetworz_wgrane(job_id, audio_bytes, nazwa, user_id, dostawca):
    """
    Pełny pipeline dla wgranego pliku, w osobnym wątku.

    Transkrypcja godzinnego nagrania trwa minuty — przeglądarka tyle nie
    poczeka, a zajęty wątek blokowałby całą aplikację.
    """
    zadanie = zadania_uploadu[job_id]
    try:
        # Własna instancja bazy: sesja SQLAlchemy nie jest bezpieczna wątkowo,
        # a ta w module obsługuje żądania HTTP.
        from database import Database as _Database
        from ai_processor import AIProcessor

        zadanie['status'] = 'transkrypcja'
        wynik = AIProcessor().process_voice_note(audio_bytes, filename=nazwa,
                                                 dostawca=dostawca)

        zadanie['status'] = 'zapis'
        wlasna_db = _Database(os.getenv('DATABASE_PATH', 'voice_notes.db'))
        notatka = wlasna_db.add_notatka(
            telegram_user_id=user_id,
            temat=wynik['temat'],
            opis=wynik['opis'],
            transkrypcja=wynik['transkrypcja'],
            segmenty=wynik.get('segmenty'),
            audio_file_id=None,          # plik nie pochodzi z Telegrama
            zadania_list=wynik['zadania'],
            embedding_vector=wynik.get('embedding'),
            cost_data=wynik.get('cost_data'),
            kategoria=wynik.get('kategoria', 'Inne'),
        )
        # Odczyt PRZED zamknięciem sesji — potem obiekt jest od niej odpięty
        # i każde sięgnięcie po atrybut kończy się DetachedInstanceError.
        notatka_id = notatka.id
        wlasna_db.close()

        zadanie.update(status='gotowe', notatka_id=notatka_id,
                       temat=wynik['temat'],
                       mowcy=sorted({s['mowca'] for s in (wynik.get('segmenty') or [])}))
        logger.info(f"Upload {job_id}: zapisano notatkę #{notatka_id}")

    except Exception as e:
        logger.error(f"Upload {job_id} nie powiódł się: {e}")
        zadanie.update(status='blad', blad=str(e)[:200])


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Wgrywanie pliku audio z pominięciem Telegrama."""
    if request.method == 'GET':
        return render_template('upload.html', max_mb=MAX_ROZMIAR_MB,
                               formaty=sorted(DOZWOLONE_FORMATY))

    plik = request.files.get('audio')
    if not plik or not plik.filename:
        return render_template('upload.html', max_mb=MAX_ROZMIAR_MB,
                               formaty=sorted(DOZWOLONE_FORMATY),
                               blad="Nie wybrano pliku")

    rozszerzenie = os.path.splitext(plik.filename)[1].lower()
    if rozszerzenie not in DOZWOLONE_FORMATY:
        return render_template('upload.html', max_mb=MAX_ROZMIAR_MB,
                               formaty=sorted(DOZWOLONE_FORMATY),
                               blad=f"Format {rozszerzenie or '(brak)'} nie jest obsługiwany")

    audio_bytes = plik.read()
    if not audio_bytes:
        return render_template('upload.html', max_mb=MAX_ROZMIAR_MB,
                               formaty=sorted(DOZWOLONE_FORMATY),
                               blad="Plik jest pusty")

    user_id = biezacy_user_id()
    dostawca = db.get_ustawienie(user_id, 'dostawca_transkrypcji',
                                 os.getenv('TRANSCRIPTION_PROVIDER', 'assemblyai'))

    job_id = uuid.uuid4().hex[:12]
    zadania_uploadu[job_id] = {'status': 'kolejka', 'nazwa': plik.filename,
                               'rozmiar': len(audio_bytes), 'user_id': user_id}
    threading.Thread(target=przetworz_wgrane, daemon=True,
                     args=(job_id, audio_bytes, plik.filename, user_id, dostawca)).start()

    logger.info(f"Upload {job_id}: {plik.filename} ({len(audio_bytes)//1024} KB), "
                f"dostawca {dostawca}")
    return redirect(url_for('upload_status', job_id=job_id))


@app.route('/upload/status/<job_id>')
@login_required
def upload_status(job_id):
    zadanie = zadania_uploadu.get(job_id)
    if not zadanie or zadanie.get('user_id') != biezacy_user_id():
        return render_template('upload.html', max_mb=MAX_ROZMIAR_MB,
                               formaty=sorted(DOZWOLONE_FORMATY),
                               blad="Nie znaleziono takiego zadania"), 404
    return render_template('upload_status.html', zadanie=zadanie, job_id=job_id)


@app.errorhandler(413)
def plik_za_duzy(_):
    return render_template('upload.html', max_mb=MAX_ROZMIAR_MB,
                           formaty=sorted(DOZWOLONE_FORMATY),
                           blad=f"Plik przekracza {MAX_ROZMIAR_MB} MB"), 413


@app.route('/statistics')
@login_required
def statistics():
    """Strona statystyk - profesjonalny dashboard z analizą AI"""
    from database import Notatka, Zadanie
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta
    import calendar

    telegram_user_id = biezacy_user_id()

    # === SEKCJA 1: Podsumowanie Kosztów ===
    notatki = db.session.query(Notatka).filter(
        Notatka.telegram_user_id == telegram_user_id,
        Notatka.deleted_at.is_(None)
    ).all()

    total_cost = 0.0
    total_tokens = 0
    total_notes = len(notatki)
    notes_with_costs = 0

    for nota in notatki:
        if nota.cost_total_usd:
            try:
                total_cost += float(nota.cost_total_usd)
                notes_with_costs += 1
            except (ValueError, TypeError):
                pass

        if nota.tokens_input or nota.tokens_output or nota.tokens_embedding:
            total_tokens += (nota.tokens_input or 0) + (nota.tokens_output or 0) + (nota.tokens_embedding or 0)

    avg_cost = total_cost / notes_with_costs if notes_with_costs > 0 else 0

    # === SEKCJA 2: Podział Kategorii ===
    category_stats = db.session.query(
        Notatka.kategoria,
        func.count(Notatka.id).label('count')
    ).filter(
        Notatka.telegram_user_id == telegram_user_id,
        Notatka.deleted_at.is_(None)
    ).group_by(Notatka.kategoria).all()

    # Oblicz koszty per kategoria
    category_data = {}
    for kategoria, count in category_stats:
        cost = sum(
            float(n.cost_total_usd) for n in notatki
            if n.kategoria == kategoria and n.cost_total_usd
        )
        percentage = (count / total_notes * 100) if total_notes > 0 else 0
        category_data[kategoria] = {
            'count': count,
            'percentage': percentage,
            'cost': cost
        }

    # === SEKCJA 3: Analiza Zadań ===
    all_tasks = db.session.query(Zadanie).join(Notatka).filter(
        Notatka.telegram_user_id == telegram_user_id,
        Notatka.deleted_at.is_(None)
    ).all()

    total_tasks = len(all_tasks)
    completed_tasks = sum(1 for t in all_tasks if t.wykonane)
    pending_tasks = total_tasks - completed_tasks
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Oblicz średni czas reakcji (tylko dla wykonanych zadań)
    reaction_times = []
    fastest_time = None
    slowest_time = None

    for task in all_tasks:
        if task.wykonane and task.data_wykonania:
            delta = (task.data_wykonania - task.notatka.data_utworzenia).total_seconds()
            days = delta / 86400  # sekundy na dni
            reaction_times.append(days)

            if fastest_time is None or days < fastest_time:
                fastest_time = days
            if slowest_time is None or days > slowest_time:
                slowest_time = days

    avg_reaction_time = sum(reaction_times) / len(reaction_times) if reaction_times else 0

    # === SEKCJA 4: Top 5 Najdroższych Notatek ===
    expensive_notes = sorted(
        [n for n in notatki if n.cost_total_usd],
        key=lambda x: float(x.cost_total_usd),
        reverse=True
    )[:5]

    top_notes = []
    for nota in expensive_notes:
        tokens_total = (nota.tokens_input or 0) + (nota.tokens_output or 0) + (nota.tokens_embedding or 0)
        top_notes.append({
            'id': nota.id,
            'temat': nota.temat,
            'kategoria': nota.kategoria,
            'data': nota.data_utworzenia.strftime('%Y-%m-%d'),
            'tokens': tokens_total,
            'cost': float(nota.cost_total_usd)
        })

    # === SEKCJA 5: Koszty w czasie (ostatnie 6 miesięcy) ===
    now = datetime.now()
    monthly_costs = {}

    for i in range(6):
        # Oblicz miesiąc i rok
        target_date = now - timedelta(days=i*30)
        month_key = target_date.strftime('%Y-%m')
        month_name = calendar.month_abbr[target_date.month]

        # Filtruj notatki z tego miesiąca
        month_notes = [
            n for n in notatki
            if n.data_utworzenia.strftime('%Y-%m') == month_key and n.cost_total_usd
        ]

        month_cost = sum(float(n.cost_total_usd) for n in month_notes)
        monthly_costs[month_name] = month_cost

    # Odwróć kolejność (najstarszy pierwszy) i przekształć na listę słowników
    monthly_costs_list = [
        {'month': month, 'cost': cost}
        for month, cost in reversed(list(monthly_costs.items()))
    ]

    # Przygotuj dane do szablonu
    stats = {
        'total_cost': total_cost,
        'total_notes': total_notes,
        'avg_cost': avg_cost,
        'total_tokens': total_tokens,
        'category_data': category_data,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'completion_rate': completion_rate,
        'avg_reaction_time': avg_reaction_time,
        'fastest_time': fastest_time,
        'slowest_time': slowest_time,
        'top_notes': top_notes,
        'monthly_costs': monthly_costs_list
    }

    return render_template('statistics.html', user=session, stats=stats)


if __name__ == '__main__':
    logger.info("🌐 Uruchamianie aplikacji webowej...")
    app.run(host='0.0.0.0', port=5000, debug=True)
