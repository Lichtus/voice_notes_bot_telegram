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
# Dostawca transkrypcji: "assemblyai" albo "openai".
#
# AssemblyAI grupuje mówców globalnie po całym nagraniu, więc etykiety są
# spójne od początku do końca. OpenAI grupuje w obrębie fragmentu i na dłuższych
# nagraniach potrafi zarówno rozjechać etykiety, jak i skleić dwie osoby w jedną.
# Cena AssemblyAI to ok. połowa stawki OpenAI. Polska transkrypcja bywa u niego
# odrobinę mniej dokładna — stąd przełącznik, a nie zamiana na sztywno.
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "assemblyai")

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ASSEMBLYAI_LANGUAGE = os.getenv("ASSEMBLYAI_LANGUAGE", "pl")

# Modele OpenAI — używane, gdy dostawcą jest "openai" albo awaryjnie.
TRANSCRIPTION_MODEL = "gpt-4o-transcribe-diarize"
WHISPER_MODEL = "whisper-1"
GPT_MODEL = "gpt-4o-mini"

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "voice_notes.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL/Supabase URL (opcjonalne)

# Prompts
EXTRACTION_PROMPT = """Jesteś moim osobistym sekretarzem i profesjonalnym skrybą. Twoim zadaniem jest przetworzenie chaotycznej transkrypcji moich notatek głosowych na uporządkowaną listę konkreów.

Zastosuj następujące zasady:
1. PERSPEKTYWA: Pisz wyłącznie w 1. osobie liczby pojedynczej (np. "Muszę zadzwonić", "Zrobię", "Zaplanowałem"). Nigdy nie używaj zwrotów typu "Użytkownik powiedział", "Notatka dotyczy".
2. STYL: Zamień potok słów na poprawną, elegancką polszczyznę. Usuń powtórzenia, wypełniacze ("eeeyy", "yyy") oraz dygresje, które nie wnoszą nic do meritum.
3. STRUKTURA: Wyciągnij informacje i pogrupuj je odpowiednio.

Transkrypcja:
"{transcription}"

Odpowiedz TYLKO w formacie JSON:
{{
  "temat": "krótki tytuł (max 80 znaków)",
  "opis": "zwięzły opis notatki w 1. osobie - streszczenie tego o czym jest notatka",
  "zadania": ["lista konkretnych zadań do wykonania - tylko to co musi być zrobione"],
  "kluczowe_mysli": ["lista najważniejszych myśli, wniosków, pomysłów"],
  "terminy": ["lista terminów, dat, spotkań, ustaleń z godzinami i osobami"],
  "kategoria": "Praca/Dom/Inne",
  "confidence": 0.85
}}

KATEGORIE:
- "Praca" - sprawy służbowe (klient, projekt, spotkanie, raport, deadline, szef, firma)
- "Dom" - sprawy prywatne (rodzina, zakupy, dom, wakacje, dziecko, małżonka)
- "Inne" - wszystko inne

WAŻNE:
- Pisz wyłącznie w 1. osobie pojedynczej
- Usuń wypełniacze i powtórzenia
- Jeśli brak danych w danej kategorii → pusta tablica: []
- Confidence to liczba 0-1 (pewność klasyfikacji kategorii)
- Zadania = to co DO ZROBIENIA (akcje)
- Kluczowe myśli = WNIOSKI i POMYSŁY (refleksje)
- Terminy = DATY, GODZINY, MIEJSCA, OSOBY
"""

DEEP_ANALYSIS_PROMPT = """Rola: Działaj jako profesjonalny analityk i dokumentator. Twoim zadaniem jest przetworzenie transkrypcji notatki głosowej (lub rozmowy) na ustrukturyzowany raport.

Zadania:

1. Identyfikacja uczestników: Jeśli w tekście występuje więcej niż jedna osoba, zidentyfikuj je i oznacz w tekście (np. Rozmówca A, Rozmówca B). Dla monologu pozostaw pustą tablicę.

2. Strukturyzacja treści: Podziel notatkę na logiczne sekcje tematyczne z nagłówkami. Każda sekcja powinna mieć podsumowanie.

3. Cytaty: W kluczowych punktach analizy przytocz dosłowne, ważne cytaty z transkrypcji (maksymalnie 3-4 na sekcję).

4. Chronologia wydarzeń: Wyodrębnij wszystkie daty i ramy czasowe pojawiające się w tekście.

5. Ustalenia: Zidentyfikuj konkretne ustalenia, decyzje i wnioski.

6. Podsumowanie: Na końcu przygotuj sekcję "Kluczowe Daty i Terminy" zbierając wszystkie terminy w jednym miejscu.

Transkrypcja:
"{transcription}"

Odpowiedz TYLKO w formacie JSON:
{{
  "tytul": "Tytuł notatki / Temat spotkania",
  "uczestnicy": ["Rozmówca A", "Rozmówca B"] lub [],
  "sekcje": [
    {{
      "naglowek": "Nazwa sekcji tematycznej",
      "tresc": "Podsumowanie sekcji",
      "cytaty": ["dosłowny cytat 1", "dosłowny cytat 2"]
    }}
  ],
  "ustalenia": ["lista osiągniętych ustaleń i wniosków"],
  "daty_chronologicznie": [
    {{"data": "YYYY-MM-DD", "wydarzenie": "Opis wydarzenia"}}
  ],
  "kluczowe_daty_podsumowanie": "Podsumowanie wszystkich terminów w jednym miejscu"
}}

WAŻNE:
- Uczestnicy pusta tablica [] dla monologu
- Sekcje muszą mieć: naglowek, tresc, cytaty (tablica)
- Daty w formacie YYYY-MM-DD lub YYYY-MM-DD HH:MM
- Cytaty dokładnie z tekstu, skróć do max 150 znaków każdy
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
