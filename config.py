"""
Konfiguracja Telegram Voice Notes Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = [int(uid) for uid in os.getenv("ALLOWED_USER_IDS", "").split(",") if uid]

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHISPER_MODEL = "whisper-1"
GPT_MODEL = "gpt-4o-mini"

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "voice_notes.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL/Supabase URL (opcjonalne)

# Prompts
EXTRACTION_PROMPT = """Przeanalizuj poniższą transkrypcję notatki głosowej i wyciągnij:
1. TEMAT (krótki tytuł, max 100 znaków)
2. OPIS (szczegółowy opis tego co użytkownik powiedział)
3. ZADANIA (lista konkretnych akcji do wykonania, jeśli są w notatce)
4. KATEGORIA (oceń do jakiej kategorii należy notatka):
   - "Praca" - sprawy zawodowe, projekty, spotkania służbowe, zadania biznesowe
   - "Dom" - sprawy domowe, rodzinne, osobiste, zakupy, hobby
   - "Inne" - wszystko inne lub gdy kategoria nie jest jasna

Transkrypcja:
"{transcription}"

Odpowiedz TYLKO w formacie JSON, bez dodatkowych komentarzy:
{{
  "temat": "krótki tytuł notatki",
  "opis": "szczegółowy opis",
  "zadania": ["zadanie 1", "zadanie 2"],
  "kategoria": "Praca/Dom/Inne"
}}

Jeśli nie ma zadań w notatce, zwróć pustą listę: "zadania": []
Kategoria musi być jedną z trzech wartości: "Praca", "Dom", "Inne"
"""

def validate_config():
    """Sprawdza czy wszystkie wymagane zmienne są ustawione"""
    errors = []

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN nie jest ustawiony w .env")

    if not ALLOWED_USER_IDS:
        errors.append("ALLOWED_USER_IDS nie jest ustawiony w .env")

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY nie jest ustawiony w .env")

    if errors:
        raise ValueError("Błędy konfiguracji:\n" + "\n".join(errors))

    return True
