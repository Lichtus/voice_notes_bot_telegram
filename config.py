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
EXTRACTION_PROMPT = """Jesteś precyzyjnym asystentem AI ds. analizy audio i notatek głosowych.

Twoim zadaniem jest przetworzenie poniższej transkrypcji (może to być dialog wieloosobowy, spotkanie biznesowe lub swobodny monolog/strumień myśli) na ustrukturyzowaną, konkretną notatkę.

ZASADY:
1. Pomiń wtrącenia, powtórzenia, zacięcia językowe i nieistotny small talk.
2. Zachowaj esencję, fakty, liczby, pomysły i kontekst wypowiedzi.
3. Dopasuj formę sekcji do typu nagrania (dialog vs. jednoosobowa notatka).
4. Nie wymyślaj informacji, których nie ma w tekście.
5. Pisz z perspektywy autora notatki — nie "użytkownik powiedział", tylko wprost o rzeczy.

TRANSKRYPCJA:
"{transcription}"

Odpowiedz TYLKO w formacie JSON:
{{
  "temat": "krótki tytuł notatki (max 80 znaków)",
  "kategoria": "Praca/Dom/Inne",
  "confidence": 0.85,
  "opis": "PODSUMOWANIE: 2-3 zwięzłe zdania opisujące główny wątek, cel lub esencję nagrania",
  "rozmowcy": [
    {{"mowca": "Rozmówca A", "podsumowanie": "co ta osoba wniosła do rozmowy, jej stanowisko i najważniejsze wypowiedzi, 1-2 zdania"}}
  ],
  "kluczowe_mysli": [
    {{"watek": "nazwa poruszonego tematu", "tresc": "najważniejsze spostrzeżenia, omówione fakty lub pomysły w tym wątku"}}
  ],
  "zadania": ["konkretne działania wynikające z wypowiedzi"],
  "terminy": ["daty, godziny i ustalenia czasowe, które nie są zadaniami"],
  "decyzje": ["decyzje, konkluzje lub definitywne przemyślenia autora"],
  "otwarte_watki": ["luźne koncepcje, wątpliwości, kwestie do sprawdzenia lub przemyślenia w przyszłości"]
}}

OBJAŚNIENIA SEKCJI:
- opis = Podsumowanie (Overview), esencja w 2-3 zdaniach
- rozmowcy = kto co mówił; WYPEŁNIJ TYLKO, gdy transkrypcja ma oznaczonych
  rozmówców (np. "Rozmówca A:"). Dla monologu zwróć pustą tablicę []
- kluczowe_mysli = Główne myśli i tematy, pogrupowane w bloki tematyczne
- zadania = Zadania i kolejne kroki, każde jako konkretne działanie
- decyzje = Kluczowe decyzje i wnioski, czyli rzeczy rozstrzygnięte
- otwarte_watki = Otwarte wątki i pomysły, czyli rzeczy nierozstrzygnięte

KATEGORIE:
- "Praca" - sprawy służbowe (klient, projekt, spotkanie, raport, deadline, szef, firma)
- "Dom" - sprawy prywatne (rodzina, zakupy, dom, wakacje, dziecko, małżonka)
- "Inne" - wszystko inne

WAŻNE:
- Jeśli brak danych w danej sekcji → pusta tablica: []
- Confidence to liczba 0-1 (pewność klasyfikacji kategorii)
- Rozróżniaj: decyzje = rozstrzygnięte, otwarte_watki = do rozstrzygnięcia
- Zadanie to AKCJA do wykonania, nie obserwacja
- Przy oznaczonych rozmówcach zachowaj ich etykiety dokładnie tak, jak
  występują w transkrypcji
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
