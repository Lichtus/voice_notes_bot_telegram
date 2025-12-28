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
from database import DatabaseManager

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
db = DatabaseManager()

# Telegram Bot Token (do pobierania zdjęć)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


@app.route('/')
def index():
    """Strona główna - przekierowanie do notatek"""
    return notes_list()


@app.route('/notes')
def notes_list():
    """Lista wszystkich notatek"""
    # Pobierz parametry z URL
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Pobierz notatki z bazy
    with db.Session() as session:
        query = session.query(db.Notatka).order_by(db.Notatka.data_utworzenia.desc())

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
                         total_notes=total_notes)


@app.route('/notes/<int:note_id>')
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


if __name__ == '__main__':
    logger.info("🌐 Uruchamianie aplikacji webowej...")
    app.run(host='0.0.0.0', port=5000, debug=True)
