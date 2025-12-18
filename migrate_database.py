#!/usr/bin/env python3
"""
Skrypt migracji bazy danych - dodaje kolumnę embedding i generuje embeddingi dla starych notatek
"""
import sqlite3
import json
from ai_processor import AIProcessor
from database import Database, Notatka

def migrate():
    print("🔄 Rozpoczynam migrację bazy danych...\n")

    # 1. Dodaj kolumnę embedding do istniejącej tabeli
    print("📝 Dodaję kolumnę 'embedding' do tabeli notatki...")

    conn = sqlite3.connect('voice_notes.db')
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE notatki ADD COLUMN embedding TEXT")
        conn.commit()
        print("✅ Kolumna 'embedding' dodana\n")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ Kolumna 'embedding' już istnieje, pomijam\n")
        else:
            raise

    conn.close()

    # 2. Wygeneruj embeddingi dla wszystkich notatek bez embeddingu
    print("🤖 Generuję embeddingi dla istniejących notatek...")

    db = Database()
    ai = AIProcessor()

    # Pobierz notatki bez embeddingu
    notatki_bez_embedding = db.session.query(Notatka).filter(
        Notatka.embedding.is_(None)
    ).all()

    if not notatki_bez_embedding:
        print("✅ Wszystkie notatki mają już embeddingi!\n")
        db.close()
        return

    print(f"📊 Znaleziono {len(notatki_bez_embedding)} notatek do aktualizacji\n")

    for i, notatka in enumerate(notatki_bez_embedding, 1):
        try:
            print(f"[{i}/{len(notatki_bez_embedding)}] Przetwarzam: {notatka.temat[:50]}...")

            # Generuj embedding
            embedding_text = f"{notatka.temat}. {notatka.opis}"
            embedding = ai.get_embedding(embedding_text)

            # Zapisz embedding
            notatka.embedding = json.dumps(embedding)
            db.session.commit()

            print(f"    ✅ Embedding wygenerowany ({len(embedding)} wymiarów)")

        except Exception as e:
            print(f"    ❌ Błąd: {e}")
            db.session.rollback()
            continue

    print("\n🎉 Migracja zakończona!")
    print(f"✅ Zaktualizowano {len(notatki_bez_embedding)} notatek")

    db.close()

if __name__ == "__main__":
    migrate()
