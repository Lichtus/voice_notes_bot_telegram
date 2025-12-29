"""
Prosty skrypt migracji - dodaje kolumny processing_time i auto_category_confidence
"""
import sqlite3
import os

DATABASE_PATH = os.getenv('DATABASE_PATH', 'voice_notes.db')

print(f"🚀 Rozpoczynam migrację dla: {DATABASE_PATH}")

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

try:
    # Sprawdź czy tabela istnieje
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notatki'")
    if not cursor.fetchone():
        print("❌ Tabela 'notatki' nie istnieje. Uruchom najpierw aplikację aby utworzyć bazę danych.")
        exit(1)

    # Pobierz istniejące kolumny
    cursor.execute("PRAGMA table_info(notatki)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"✓ Znaleziono {len(columns)} kolumn w tabeli 'notatki'")

    # Dodaj processing_time jeśli nie istnieje
    if 'processing_time' not in columns:
        print("➕ Dodaję kolumnę 'processing_time'...")
        cursor.execute("ALTER TABLE notatki ADD COLUMN processing_time TEXT")
        print("✅ Dodano 'processing_time'")
    else:
        print("✓ Kolumna 'processing_time' już istnieje")

    # Dodaj auto_category_confidence jeśli nie istnieje
    if 'auto_category_confidence' not in columns:
        print("➕ Dodaję kolumnę 'auto_category_confidence'...")
        cursor.execute("ALTER TABLE notatki ADD COLUMN auto_category_confidence TEXT")
        print("✅ Dodano 'auto_category_confidence'")
    else:
        print("✓ Kolumna 'auto_category_confidence' już istnieje")

    conn.commit()
    print("🎉 Migracja zakończona pomyślnie!")

except Exception as e:
    print(f"❌ Błąd: {e}")
    conn.rollback()
    exit(1)
finally:
    conn.close()
