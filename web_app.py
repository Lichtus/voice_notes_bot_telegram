#!/usr/bin/env python3
"""
Voice Notes Bot - Web Application
Aplikacja webowa do przeglądania notatek głosowych
"""

import os
import logging
from functools import wraps
from datetime import datetime
import json

from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify, Response
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

# Import modułów bota
from database import DatabaseManager

# Konfiguracja
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicjalizacja bazy danych
db = DatabaseManager()

# Dane logowania (w produkcji użyj bazy danych lub .env)
WEB_USERNAME = os.getenv('WEB_USERNAME', 'admin')
WEB_PASSWORD_HASH = generate_password_hash(os.getenv('WEB_PASSWORD', 'admin'))

# Telegram Bot Token (do pobierania zdjęć)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


def login_required(f):
    """Dekorator wymagający zalogowania"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Strona główna - przekierowanie do notatek lub logowania"""
    if 'logged_in' in session:
        return redirect(url_for('notes_list'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Strona logowania"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == WEB_USERNAME and check_password_hash(WEB_PASSWORD_HASH, password):
            session['logged_in'] = True
            session['username'] = username
            next_page = request.args.get('next')
            return redirect(next_page or url_for('notes_list'))
        else:
            return render_template('login.html', error='Nieprawidłowa nazwa użytkownika lub hasło')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Wylogowanie"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/notes')
@login_required
def notes_list():
    """Lista wszystkich notatek"""
    # Pobierz parametry z URL
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('q', '').strip()

    # Pobierz notatki z bazy
    with db.Session() as session:
        query = session.query(db.Notatka).order_by(db.Notatka.data_utworzenia.desc())

        # Filtrowanie po zapytaniu wyszukiwania
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                db.Notatka.temat.ilike(search_pattern) |
                db.Notatka.opis.ilike(search_pattern)
            )

        # Paginacja
        total_notes = query.count()
        total_pages = (total_notes + per_page - 1) // per_page
        notes = query.offset((page - 1) * per_page).limit(per_page).all()

        # Przygotuj dane notatek
        notes_data = []
        for note in notes:
            zadania_list = json.loads(note.zadania) if note.zadania else []
            photo_count = len(json.loads(note.photo_file_ids)) if note.photo_file_ids else 0

            notes_data.append({
                'id': note.id,
                'temat': note.temat,
                'opis': note.opis[:200] + '...' if len(note.opis) > 200 else note.opis,
                'data_utworzenia': note.data_utworzenia,
                'zadania_count': len(zadania_list),
                'photo_count': photo_count
            })

    return render_template('notes_list.html',
                         notes=notes_data,
                         page=page,
                         total_pages=total_pages,
                         search_query=search_query,
                         total_notes=total_notes)


@app.route('/notes/<int:note_id>')
@login_required
def note_detail(note_id):
    """Szczegóły pojedynczej notatki"""
    with db.Session() as session:
        note = session.query(db.Notatka).filter_by(id=note_id).first()

        if not note:
            return "Notatka nie znaleziona", 404

        # Przygotuj dane
        zadania_list = json.loads(note.zadania) if note.zadania else []
        photo_file_ids = json.loads(note.photo_file_ids) if note.photo_file_ids else []

        note_data = {
            'id': note.id,
            'temat': note.temat,
            'opis': note.opis,
            'transkrypcja': note.transkrypcja,
            'data_utworzenia': note.data_utworzenia,
            'zadania': zadania_list,
            'photo_file_ids': photo_file_ids,
            'has_photos': len(photo_file_ids) > 0
        }

    return render_template('note_detail.html', note=note_data)


@app.route('/notes/<int:note_id>/photo/<int:photo_index>')
@login_required
async def get_photo(note_id, photo_index):
    """Pobierz zdjęcie z Telegram i wyślij jako odpowiedź"""
    import httpx

    with db.Session() as session:
        note = session.query(db.Notatka).filter_by(id=note_id).first()

        if not note or not note.photo_file_ids:
            return "Zdjęcie nie znalezione", 404

        photo_file_ids = json.loads(note.photo_file_ids)

        if photo_index < 0 or photo_index >= len(photo_file_ids):
            return "Nieprawidłowy indeks zdjęcia", 404

        file_id = photo_file_ids[photo_index]

        try:
            # Pobierz informacje o pliku z Telegram
            async with httpx.AsyncClient() as client:
                # Pobierz ścieżkę do pliku
                file_response = await client.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
                    params={'file_id': file_id}
                )
                file_data = file_response.json()

                if not file_data.get('ok'):
                    logger.error(f"Błąd pobierania pliku z Telegram: {file_data}")
                    return "Błąd pobierania zdjęcia", 500

                file_path = file_data['result']['file_path']

                # Pobierz sam plik
                photo_response = await client.get(
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


@app.route('/notes/<int:note_id>/pdf')
@login_required
async def generate_note_pdf(note_id):
    """Generuj i pobierz PDF notatki"""
    from weasyprint import HTML, CSS
    import tempfile
    import base64
    import httpx

    with db.Session() as session:
        note = session.query(db.Notatka).filter_by(id=note_id).first()

        if not note:
            return "Notatka nie znaleziona", 404

        # Przygotuj dane
        zadania_list = json.loads(note.zadania) if note.zadania else []
        photo_file_ids = json.loads(note.photo_file_ids) if note.photo_file_ids else []

        # Pobierz zdjęcia i przekonwertuj na base64
        photos_html = ""
        if photo_file_ids:
            photos_html = "<div class='photos'><h2>📸 Zdjęcia</h2>"

            async with httpx.AsyncClient() as client:
                for i, file_id in enumerate(photo_file_ids, 1):
                    try:
                        # Pobierz ścieżkę do pliku
                        file_response = await client.get(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
                            params={'file_id': file_id}
                        )
                        file_data = file_response.json()

                        if file_data.get('ok'):
                            file_path = file_data['result']['file_path']

                            # Pobierz plik
                            photo_response = await client.get(
                                f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                            )

                            if photo_response.status_code == 200:
                                # Konwertuj do base64
                                photo_base64 = base64.b64encode(photo_response.content).decode('utf-8')
                                photos_html += f'<img src="data:image/jpeg;base64,{photo_base64}" alt="Zdjęcie {i}" />'

                    except Exception as e:
                        logger.error(f"Błąd pobierania zdjęcia {i}: {e}")
                        photos_html += f'<p class="error">❌ Błąd wczytywania zdjęcia {i}</p>'

            photos_html += "</div>"

        # Formatuj zadania
        zadania_html = ""
        if zadania_list:
            zadania_html = "<div class='zadania'><h2>📋 Zadania</h2><ul>"
            for zadanie in zadania_list:
                zadania_html += f"<li>{zadanie}</li>"
            zadania_html += "</ul></div>"

        # Szablon HTML (taki sam jak w bocie)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Notatka #{note.id}</title>
        </head>
        <body>
            <div class="header">
                <h1>📝 Notatka #{note.id}</h1>
                <p class="date">📅 {note.data_utworzenia.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="content">
                <div class="section">
                    <h2>📌 Temat</h2>
                    <p class="temat">{note.temat}</p>
                </div>

                <div class="section">
                    <h2>📝 Opis</h2>
                    <p class="opis">{note.opis}</p>
                </div>

                {zadania_html}

                {photos_html}
            </div>

            <div class="footer">
                <p>Wygenerowano przez Voice Notes Bot</p>
            </div>
        </body>
        </html>
        """

        # CSS (taki sam jak w bocie)
        css_content = """
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #333;
        }

        .header {
            text-align: center;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .header h1 {
            color: #4CAF50;
            font-size: 28pt;
            margin: 0;
        }

        .date {
            color: #666;
            font-size: 11pt;
            margin-top: 10px;
        }

        .section {
            margin-bottom: 30px;
        }

        h2 {
            color: #2196F3;
            font-size: 16pt;
            border-bottom: 2px solid #E3F2FD;
            padding-bottom: 5px;
            margin-bottom: 15px;
        }

        .temat {
            font-size: 14pt;
            font-weight: bold;
            color: #333;
        }

        .opis {
            text-align: justify;
            white-space: pre-wrap;
        }

        .zadania ul {
            list-style-type: none;
            padding-left: 0;
        }

        .zadania li {
            padding: 10px;
            margin: 5px 0;
            background-color: #FFF9C4;
            border-left: 4px solid #FBC02D;
            border-radius: 4px;
        }

        .zadania li::before {
            content: "☐ ";
            font-weight: bold;
            color: #FBC02D;
        }

        .photos {
            margin-top: 30px;
        }

        .photos img {
            max-width: 100%;
            height: auto;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            page-break-inside: avoid;
        }

        .error {
            color: #f44336;
            font-style: italic;
        }

        .footer {
            margin-top: 50px;
            text-align: center;
            font-size: 10pt;
            color: #999;
            border-top: 1px solid #ddd;
            padding-top: 20px;
        }
        """

        # Generuj PDF
        html = HTML(string=html_content)
        css = CSS(string=css_content)
        pdf_bytes = html.write_pdf(stylesheets=[css])

        # Zwróć PDF jako plik do pobrania
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=notatka_{note.id}.pdf'
            }
        )


if __name__ == '__main__':
    logger.info("🌐 Uruchamianie aplikacji webowej...")
    app.run(host='0.0.0.0', port=5000, debug=True)
