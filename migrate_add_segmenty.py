#!/usr/bin/env python3
"""
Dodaje kolumnę transkrypcja_segmenty (diaryzacja — podział na mówców).

Świeża baza dostaje ją automatycznie z create_all(); ten skrypt jest potrzebny
wyłącznie dla baz założonych wcześniej.

    python3 migrate_add_segmenty.py [ścieżka_do_bazy]
"""
import sqlite3
import sys

BAZA = sys.argv[1] if len(sys.argv) > 1 else "data/voice_notes.db"

conn = sqlite3.connect(BAZA)
istniejace = [k[1] for k in conn.execute("PRAGMA table_info(notatki)")]

if "transkrypcja_segmenty" in istniejace:
    print(f"{BAZA}: kolumna transkrypcja_segmenty już istnieje — nic do zrobienia")
else:
    conn.execute("ALTER TABLE notatki ADD COLUMN transkrypcja_segmenty TEXT")
    conn.commit()
    print(f"{BAZA}: dodano kolumnę transkrypcja_segmenty")

print("kolumn łącznie:", len([k[1] for k in conn.execute("PRAGMA table_info(notatki)")]))
conn.close()
