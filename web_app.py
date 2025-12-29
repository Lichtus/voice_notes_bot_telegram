#!/usr/bin/env python3
"""
Voice Notes Bot - Web Application
Aplikacja webowa do przeglądania notatek głosowych
"""

import os
import logging
from datetime import datetime
import json

from flask import Flask, render_template, request, Response
from dotenv import load_dotenv

# Import modułów bota
from database import Database

# Konfiguracja
load_dotenv()

app = Flask(__name__)

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


@app.route('/')
def index():
    """Strona główna - przekierowanie do notatek"""
    return notes_list()


@app.route('/notes')
def notes_list():
    """Lista wszystkich notatek z wyszukiwaniem, filtrowaniem i sortowaniem"""
    from database import Notatka, Zadanie
    from sqlalchemy import func, or_
    from datetime import timedelta

    # Pobierz parametry z URL
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '', type=str).strip()
    date_filter = request.args.get('date_filter', 'all', type=str)
    tasks_filter = request.args.get('tasks_filter', 'all', type=str)
    sort_by = request.args.get('sort', 'date_desc', type=str)

    # Buduj zapytanie
    query = db.session.query(Notatka)

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
                         sort_by=sort_by)


@app.route('/notes/<int:note_id>')
def note_detail(note_id):
    """Szczegóły pojedynczej notatki"""
    from database import Notatka
    note = db.session.query(Notatka).filter_by(id=note_id).first()

    if not note:
        return "Notatka nie znaleziona", 404

    # Przygotuj dane - note.zadania to relacja ORM do obiektów Zadanie
    zadania_list = [z.zadanie for z in note.zadania] if note.zadania else []
    photo_file_ids = json.loads(note.photo_file_ids) if note.photo_file_ids else []

    # Sprawdź czy notatka była edytowana
    is_edited = '✏️ *Edytowano:*' in note.opis if note.opis else False
    edit_date = None
    if is_edited:
        # Ekstrahuj datę edycji z opisu
        import re
        match = re.search(r'✏️ \*Edytowano:\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', note.opis)
        if match:
            edit_date = match.group(1)

    note_data = {
        'id': note.id,
        'temat': note.temat,
        'opis': note.opis,
        'transkrypcja': note.transkrypcja,
        'data_utworzenia': note.data_utworzenia,
        'zadania': zadania_list,
        'photo_file_ids': photo_file_ids,
        'has_photos': len(photo_file_ids) > 0,
        'is_edited': is_edited,
        'edit_date': edit_date
    }

    return render_template('note_detail.html', note=note_data)


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
def prepare_email(note_id):
    """Przygotuj mailto link z notatką"""
    import urllib.parse
    from database import Notatka

    note = db.session.query(Notatka).filter_by(id=note_id).first()

    if not note:
        return "Notatka nie znaleziona", 404

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
def get_photo(note_id, photo_index):
    """Pobierz zdjęcie z Telegram i wyślij jako odpowiedź"""
    import requests
    from database import Notatka

    note = db.session.query(Notatka).filter_by(id=note_id).first()

    if not note or not note.photo_file_ids:
        return "Zdjęcie nie znalezione", 404

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


if __name__ == '__main__':
    logger.info("🌐 Uruchamianie aplikacji webowej...")
    app.run(host='0.0.0.0', port=5000, debug=True)
