#!/usr/bin/env python3
"""
Dodaje kolumny decyzje i otwarte_watki (nowe sekcje podsumowania).

Świeża baza dostaje je z create_all(); ten skrypt jest dla baz istniejących.

    python3 migrate_add_sekcje.py [ścieżka_do_bazy]
"""
import sqlite3
import sys

BAZA = sys.argv[1] if len(sys.argv) > 1 else "data/voice_notes.db"
NOWE = {"decyzje": "TEXT", "otwarte_watki": "TEXT"}

conn = sqlite3.connect(BAZA)
istniejace = [k[1] for k in conn.execute("PRAGMA table_info(notatki)")]

for kolumna, typ in NOWE.items():
    if kolumna in istniejace:
        print(f"{BAZA}: {kolumna} już istnieje")
    else:
        conn.execute(f"ALTER TABLE notatki ADD COLUMN {kolumna} {typ}")
        print(f"{BAZA}: dodano {kolumna}")
conn.commit()
print("kolumn łącznie:", len([k[1] for k in conn.execute("PRAGMA table_info(notatki)")]))
conn.close()
