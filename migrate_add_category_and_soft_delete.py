"""
Skrypt migracji: Dodaje kolumny 'kategoria' i 'deleted_at' do tabeli notatki

Uruchom ten skrypt, aby zaktualizować istniejącą bazę danych.
"""
import logging
from sqlalchemy import create_engine, text, inspect
from config import DATABASE_PATH, DATABASE_URL

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run_migration():
    """Wykonuje migrację bazy danych"""

    # Połącz się z bazą
    if DATABASE_URL:
        engine = create_engine(DATABASE_URL, echo=False)
        db_type = "postgresql"
        logger.info(f"🔗 Łączenie z PostgreSQL (Supabase)...")
    else:
        engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
        db_type = "sqlite"
        logger.info(f"🔗 Łączenie z SQLite ({DATABASE_PATH})...")

    # Sprawdź istniejące kolumny
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('notatki')]

    logger.info(f"📋 Obecne kolumny w tabeli notatki: {', '.join(columns)}")

    with engine.connect() as conn:
        # Sprawdź i dodaj kolumnę 'kategoria'
        if 'kategoria' not in columns:
            logger.info("➕ Dodawanie kolumny 'kategoria'...")

            if db_type == "sqlite":
                # SQLite
                conn.execute(text("ALTER TABLE notatki ADD COLUMN kategoria VARCHAR(50) DEFAULT 'Inne' NOT NULL"))
            else:
                # PostgreSQL
                conn.execute(text("ALTER TABLE notatki ADD COLUMN kategoria VARCHAR(50) DEFAULT 'Inne' NOT NULL"))

            conn.commit()
            logger.info("✅ Kolumna 'kategoria' dodana pomyślnie!")
        else:
            logger.info("ℹ️  Kolumna 'kategoria' już istnieje, pomijam.")

        # Sprawdź i dodaj kolumnę 'deleted_at'
        if 'deleted_at' not in columns:
            logger.info("➕ Dodawanie kolumny 'deleted_at'...")

            if db_type == "sqlite":
                # SQLite
                conn.execute(text("ALTER TABLE notatki ADD COLUMN deleted_at TIMESTAMP NULL"))
            else:
                # PostgreSQL
                conn.execute(text("ALTER TABLE notatki ADD COLUMN deleted_at TIMESTAMP NULL"))

            conn.commit()
            logger.info("✅ Kolumna 'deleted_at' dodana pomyślnie!")
        else:
            logger.info("ℹ️  Kolumna 'deleted_at' już istnieje, pomijam.")

    logger.info("🎉 Migracja zakończona pomyślnie!")
    logger.info("")
    logger.info("📝 Co zostało dodane:")
    logger.info("   - kategoria: Kategoria notatki (Praca, Dom, Inne)")
    logger.info("   - deleted_at: Data usunięcia (NULL = aktywna)")
    logger.info("")
    logger.info("💡 Wszystkie istniejące notatki otrzymały kategorię 'Inne'")
    logger.info("💡 Możesz teraz używać funkcji kategoryzacji i soft delete")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        logger.error(f"❌ Błąd podczas migracji: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
