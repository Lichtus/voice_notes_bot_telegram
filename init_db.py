"""
Inicjalizacja bazy danych - tworzenie tabel
"""
from database import Base, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("🚀 Tworzenie tabel w bazie danych...")
    Base.metadata.create_all(engine)
    logger.info("✅ Tabele zostały utworzone pomyślnie!")
