#!/usr/bin/env python3
"""
Skrypt migracji: Dodanie kolumn kosztów API do tabeli notatki
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = "voice_notes.db"

def migrate():
    """Dodaje kolumny kosztów do tabeli notatki"""

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Lista kolumn do dodania
    columns_to_add = [
        ("audio_duration_seconds", "INTEGER"),
        ("tokens_input", "INTEGER"),
        ("tokens_output", "INTEGER"),
        ("tokens_embedding", "INTEGER"),
        ("cost_whisper_usd", "TEXT"),
        ("cost_gpt_input_usd", "TEXT"),
        ("cost_gpt_output_usd", "TEXT"),
        ("cost_embedding_usd", "TEXT"),
        ("cost_total_usd", "TEXT"),
    ]

    # Sprawdź które kolumny już istnieją
    cursor.execute("PRAGMA table_info(notatki)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    logger.info(f"Istniejące kolumny: {existing_columns}")

    # Dodaj brakujące kolumny
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                sql = f"ALTER TABLE notatki ADD COLUMN {column_name} {column_type}"
                logger.info(f"Wykonuję: {sql}")
                cursor.execute(sql)
                logger.info(f"✅ Dodano kolumnę: {column_name}")
            except sqlite3.Error as e:
                logger.error(f"❌ Błąd dodawania kolumny {column_name}: {e}")
        else:
            logger.info(f"⏭️  Kolumna {column_name} już istnieje, pomijam")

    conn.commit()
    conn.close()

    logger.info("🎉 Migracja zakończona!")

if __name__ == "__main__":
    logger.info("🚀 Rozpoczynam migrację bazy danych...")
    migrate()
