#!/usr/bin/env python3
"""
Skrypt do migracji danych z SQLite do Supabase (PostgreSQL)
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Notatka, Zadanie
from config import DATABASE_PATH, DATABASE_URL

def migrate_data():
    """Migruje dane z SQLite do Supabase"""

    if not DATABASE_URL:
        print("❌ Błąd: DATABASE_URL nie jest ustawione w .env")
        print("Dodaj linię do .env:")
        print("DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres")
        sys.exit(1)

    print("🔄 Migracja danych z SQLite do Supabase\n")

    # Połączenie ze SQLite (źródło)
    print(f"📂 Otwieram SQLite: {DATABASE_PATH}")
    sqlite_engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SQLiteSession()

    # Połączenie z PostgreSQL/Supabase (cel)
    print(f"🌐 Łączę z Supabase...")
    postgres_engine = create_engine(DATABASE_URL, echo=False)

    # Utwórz tabele w PostgreSQL jeśli nie istnieją
    Base.metadata.create_all(postgres_engine)

    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()

    try:
        # Pobierz wszystkie notatki z SQLite
        notatki = sqlite_session.query(Notatka).all()
        print(f"\n📝 Znaleziono {len(notatki)} notatek w SQLite")

        if len(notatki) == 0:
            print("ℹ️  Brak notatek do migracji")
            return

        # Sprawdź czy Supabase już ma dane
        existing_count = postgres_session.query(Notatka).count()
        if existing_count > 0:
            response = input(f"\n⚠️  UWAGA: Supabase już zawiera {existing_count} notatek!\n"
                           f"Czy chcesz kontynuować? Może to spowodować duplikaty. (tak/nie): ")
            if response.lower() not in ['tak', 't', 'yes', 'y']:
                print("❌ Anulowano")
                return

        # Migruj notatki
        migrated = 0
        for old_note in notatki:
            # Stwórz nową notatkę (bez ID - PostgreSQL sam ustawi)
            new_note = Notatka(
                telegram_user_id=old_note.telegram_user_id,
                data_utworzenia=old_note.data_utworzenia,
                temat=old_note.temat,
                opis=old_note.opis,
                transkrypcja=old_note.transkrypcja,
                audio_file_id=old_note.audio_file_id,
                embedding=old_note.embedding
            )

            # Dodaj zadania
            for old_task in old_note.zadania:
                new_task = Zadanie(
                    zadanie=old_task.zadanie,
                    wykonane=old_task.wykonane,
                    data_wykonania=old_task.data_wykonania
                )
                new_note.zadania.append(new_task)

            postgres_session.add(new_note)
            migrated += 1
            print(f"✅ {migrated}/{len(notatki)}: {old_note.temat[:50]}...")

        # Commit wszystkich zmian
        postgres_session.commit()

        print(f"\n🎉 Sukces! Zmigrowano {migrated} notatek do Supabase")
        print("\n📊 Podsumowanie:")

        # Statystyki
        total_notes = postgres_session.query(Notatka).count()
        total_tasks = postgres_session.query(Zadanie).count()

        print(f"   📝 Wszystkich notatek w Supabase: {total_notes}")
        print(f"   📋 Wszystkich zadań w Supabase: {total_tasks}")

        print("\n✅ Migracja zakończona!")
        print("\nNastępne kroki:")
        print("1. Sprawdź dane w Supabase Dashboard")
        print("2. Restart bota: sudo systemctl restart voice-notes-bot")
        print("3. Sprawdź logi: sudo journalctl -u voice-notes-bot -n 20")

    except Exception as e:
        print(f"\n❌ Błąd podczas migracji: {e}")
        postgres_session.rollback()
        sys.exit(1)
    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    migrate_data()
