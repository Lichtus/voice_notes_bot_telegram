"""
Migracja bazy danych - dodanie pól processing_time i auto_category_confidence
"""
import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ścieżka do bazy danych
DATABASE_PATH = os.getenv('DATABASE_PATH', 'voice_notes.db')
DATABASE_URL = os.getenv('DATABASE_URL', None)


def migrate_sqlite():
    """Migracja dla SQLite"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Sprawdź czy kolumny już istnieją
        cursor.execute("PRAGMA table_info(notatki)")
        columns = [row[1] for row in cursor.fetchall()]

        # Dodaj processing_time jeśli nie istnieje
        if 'processing_time' not in columns:
            logger.info("Dodaję kolumnę 'processing_time'...")
            cursor.execute("ALTER TABLE notatki ADD COLUMN processing_time TEXT")
            logger.info("✅ Dodano kolumnę 'processing_time'")
        else:
            logger.info("✓ Kolumna 'processing_time' już istnieje")

        # Dodaj auto_category_confidence jeśli nie istnieje
        if 'auto_category_confidence' not in columns:
            logger.info("Dodaję kolumnę 'auto_category_confidence'...")
            cursor.execute("ALTER TABLE notatki ADD COLUMN auto_category_confidence TEXT")
            logger.info("✅ Dodano kolumnę 'auto_category_confidence'")
        else:
            logger.info("✓ Kolumna 'auto_category_confidence' już istnieje")

        conn.commit()
        logger.info("🎉 Migracja SQLite zakończona pomyślnie!")

    except Exception as e:
        logger.error(f"❌ Błąd migracji: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate_postgresql():
    """Migracja dla PostgreSQL (Supabase)"""
    try:
        import psycopg2
        from urllib.parse import urlparse

        # Parse DATABASE_URL
        url = urlparse(DATABASE_URL)

        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            user=url.username,
            password=url.password,
            database=url.path[1:]  # Remove leading '/'
        )
        cursor = conn.cursor()

        try:
            # Sprawdź czy kolumny już istnieją
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='notatki'
            """)
            columns = [row[0] for row in cursor.fetchall()]

            # Dodaj processing_time jeśli nie istnieje
            if 'processing_time' not in columns:
                logger.info("Dodaję kolumnę 'processing_time'...")
                cursor.execute("ALTER TABLE notatki ADD COLUMN processing_time TEXT")
                logger.info("✅ Dodano kolumnę 'processing_time'")
            else:
                logger.info("✓ Kolumna 'processing_time' już istnieje")

            # Dodaj auto_category_confidence jeśli nie istnieje
            if 'auto_category_confidence' not in columns:
                logger.info("Dodaję kolumnę 'auto_category_confidence'...")
                cursor.execute("ALTER TABLE notatki ADD COLUMN auto_category_confidence TEXT")
                logger.info("✅ Dodano kolumnę 'auto_category_confidence'")
            else:
                logger.info("✓ Kolumna 'auto_category_confidence' już istnieje")

            conn.commit()
            logger.info("🎉 Migracja PostgreSQL zakończona pomyślnie!")

        except Exception as e:
            logger.error(f"❌ Błąd migracji: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    except ImportError:
        logger.error("❌ Brak biblioteki psycopg2. Zainstaluj: pip install psycopg2-binary")
        raise


if __name__ == '__main__':
    logger.info("🚀 Rozpoczynam migrację bazy danych...")

    if DATABASE_URL:
        logger.info("📊 Wykryto PostgreSQL/Supabase")
        migrate_postgresql()
    else:
        logger.info("📊 Wykryto SQLite")
        migrate_sqlite()

    logger.info("✨ Wszystko gotowe!")
