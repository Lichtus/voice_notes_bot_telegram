"""
Skrypt migracji: Dodaje kolumny 'kategoria' i 'deleted_at' do tabeli notatki
Używa wbudowanego modułu sqlite3 (bez dodatkowych zależności)
"""
import sqlite3
import os

# Ścieżka do bazy danych
DB_PATH = os.getenv('DATABASE_PATH', 'voice_notes.db')

print(f"🔗 Łączenie z bazą danych: {DB_PATH}")

try:
    # Sprawdź czy baza danych istnieje i nie jest pusta
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        print("ℹ️  Baza danych nie istnieje lub jest pusta")
        print("💡 Nowe kolumny zostaną dodane automatycznie przy pierwszym uruchomieniu bota/web app")
        exit(0)

    # Połącz się z bazą
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Sprawdź czy tabela notatki istnieje
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notatki'")
    if not cursor.fetchone():
        print("ℹ️  Tabela 'notatki' nie istnieje")
        print("💡 Zostanie utworzona automatycznie przy pierwszym uruchomieniu bota/web app")
        conn.close()
        exit(0)

    # Sprawdź obecne kolumny
    cursor.execute("PRAGMA table_info(notatki)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"📋 Obecne kolumny: {', '.join(columns)}")

    # Dodaj kolumnę 'kategoria' jeśli nie istnieje
    if 'kategoria' not in columns:
        print("➕ Dodawanie kolumny 'kategoria'...")
        cursor.execute("ALTER TABLE notatki ADD COLUMN kategoria VARCHAR(50) DEFAULT 'Inne' NOT NULL")
        conn.commit()
        print("✅ Kolumna 'kategoria' dodana!")
    else:
        print("ℹ️  Kolumna 'kategoria' już istnieje")

    # Dodaj kolumnę 'deleted_at' jeśli nie istnieje
    if 'deleted_at' not in columns:
        print("➕ Dodawanie kolumny 'deleted_at'...")
        cursor.execute("ALTER TABLE notatki ADD COLUMN deleted_at TIMESTAMP NULL")
        conn.commit()
        print("✅ Kolumna 'deleted_at' dodana!")
    else:
        print("ℹ️  Kolumna 'deleted_at' już istnieje")

    # Sprawdź zaktualizowane kolumny
    cursor.execute("PRAGMA table_info(notatki)")
    updated_columns = [col[1] for col in cursor.fetchall()]
    print(f"\n📋 Zaktualizowane kolumny: {', '.join(updated_columns)}")

    conn.close()

    print("\n🎉 Migracja zakończona pomyślnie!")
    print("\n📝 Co zostało dodane:")
    print("   - kategoria: Kategoria notatki (Praca, Dom, Inne)")
    print("   - deleted_at: Data usunięcia (NULL = aktywna)")
    print("\n💡 Wszystkie istniejące notatki otrzymały kategorię 'Inne'")

except Exception as e:
    print(f"❌ Błąd podczas migracji: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
