#!/usr/bin/env python3
"""
Migracja: Dodanie pól kluczowe_mysli i terminy do tabeli notatki
"""

from sqlalchemy import create_engine, Column, Text, text
from database import Base, Notatka
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "voice_notes.db")

# Dodaj nowe kolumny
engine = create_engine(f'sqlite:///{DATABASE_PATH}')

# Sprawdź czy kolumny już istnieją
with engine.connect() as conn:
    result = conn.execute(text("PRAGMA table_info(notatki)"))
    columns = [row[1] for row in result]

    if 'kluczowe_mysli' not in columns:
        print("Dodaję kolumnę 'kluczowe_mysli'...")
        conn.execute(text("ALTER TABLE notatki ADD COLUMN kluczowe_mysli TEXT"))
        conn.commit()
        print("✅ Dodano 'kluczowe_mysli'")
    else:
        print("ℹ️ Kolumna 'kluczowe_mysli' już istnieje")

    if 'terminy' not in columns:
        print("Dodaję kolumnę 'terminy'...")
        conn.execute(text("ALTER TABLE notatki ADD COLUMN terminy TEXT"))
        conn.commit()
        print("✅ Dodano 'terminy'")
    else:
        print("ℹ️ Kolumna 'terminy' już istnieje")

print("\n✅ Migracja zakończona!")
