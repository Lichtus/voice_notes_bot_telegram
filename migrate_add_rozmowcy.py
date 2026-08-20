#!/usr/bin/env python3
"""Dodaje kolumnę rozmowcy (podsumowanie wypowiedzi każdej osoby)."""
import sqlite3
import sys

BAZA = sys.argv[1] if len(sys.argv) > 1 else "data/voice_notes.db"
conn = sqlite3.connect(BAZA)
if "rozmowcy" in [k[1] for k in conn.execute("PRAGMA table_info(notatki)")]:
    print(f"{BAZA}: kolumna rozmowcy już istnieje")
else:
    conn.execute("ALTER TABLE notatki ADD COLUMN rozmowcy TEXT")
    conn.commit()
    print(f"{BAZA}: dodano kolumnę rozmowcy")
conn.close()
