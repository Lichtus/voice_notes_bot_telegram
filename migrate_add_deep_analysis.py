#!/usr/bin/env python3
"""
Migracja: Dodanie pól analizy głębokiej do tabeli notatki
Dodaje kolumny dla dogłębnej analizy długich notatek głosowych (>5 minut)
"""

from sqlalchemy import create_engine, Column, Text, Boolean, text
from database import Base, Notatka
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "voice_notes.db")
DATABASE_URL = os.getenv("DATABASE_URL")

# Wybierz odpowiedni silnik bazy danych
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    print("💾 Używam bazy danych: PostgreSQL (Supabase)")
else:
    engine = create_engine(f'sqlite:///{DATABASE_PATH}')
    print(f"💾 Używam bazy danych: SQLite ({DATABASE_PATH})")

# Sprawdź czy kolumny już istnieją
with engine.connect() as conn:
    if DATABASE_URL:
        # PostgreSQL - użyj information_schema
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'notatki'
        """))
        columns = [row[0] for row in result]
    else:
        # SQLite - użyj PRAGMA
        result = conn.execute(text("PRAGMA table_info(notatki)"))
        columns = [row[1] for row in result]

    # Lista kolumn do dodania
    new_columns = [
        ('czy_analizowane', 'BOOLEAN DEFAULT FALSE'),
        ('analiza_tytul', 'TEXT'),
        ('analiza_uczestnicy', 'TEXT'),
        ('analiza_sekcje', 'TEXT'),
        ('analiza_ustalenia', 'TEXT'),
        ('analiza_daty_chronologicznie', 'TEXT'),
        ('analiza_podsumowanie_dat', 'TEXT'),
    ]

    for column_name, column_type in new_columns:
        if column_name not in columns:
            print(f"Dodaję kolumnę '{column_name}'...")
            if DATABASE_URL:
                # PostgreSQL
                default_clause = " DEFAULT FALSE" if column_type.startswith("BOOLEAN") else ""
                conn.execute(text(f"ALTER TABLE notatki ADD COLUMN {column_name} {column_type}{default_clause}"))
            else:
                # SQLite
                conn.execute(text(f"ALTER TABLE notatki ADD COLUMN {column_name} {column_type}"))
            conn.commit()
            print(f"✅ Dodano '{column_name}'")
        else:
            print(f"ℹ️ Kolumna '{column_name}' już istnieje")

print("\n✅ Migracja zakończona!")
print("Dodano pola analizy głębokiej dla długich notatek głosowych.")
