# Plan: Analiza Długich Notatek (>5 minut)

**Data:** 2026-01-16
**Status:** Planowanie

## Cel

Dodanie funkcji dogłębnej analizy dla długich notatek głosowych (powyżej 5 minut). System automatycznie zapyta użytkownika czy przeprowadzić szczegółową analizę z identyfikacją uczestników, sekcjami tematycznymi, cytatami i chronologią.

## Prompt do Analizy

```
Rola: Działaj jako profesjonalny analityk i dokumentator. Twoim zadaniem jest przetworzenie transkrypcji notatki głosowej (lub rozmowy) na ustrukturyzowany raport.

Zadania:

1. Identyfikacja uczestników: Jeśli w tekście występuje więcej niż jedna osoba, zidentyfikuj je i oznacz w tekście (np. Rozmówca A, Rozmówca B), zachowując formę dialogu tam, gdzie jest to istotne dla kontekstu.

2. Strukturyzacja treści: Podziel notatkę na logiczne sekcje tematyczne z nagłówkami.

3. Cytaty: W kluczowych punktach analizy przytocz dosłowne, ważne cytaty z transkrypcji, aby zachować autentyczność wypowiedzi.

4. Chronologia wydarzeń: Wyodrębnij wszystkie daty i ramy czasowe pojawiające się w tekście. Stwórz z nich uporządkowaną listę chronologiczną.

5. Podsumowanie: Na końcu dokumentu przygotuj sekcję "Kluczowe Daty i Terminy", która zbierze wszystkie ramy czasowe w jednym miejscu.
```

## Struktura JSON Wyniku

```json
{
  "tytul": "Tytuł notatki / Temat spotkania",
  "uczestnicy": ["Lista uczestników lub pusta tablica dla monologu"],
  "sekcje": [
    {
      "naglowek": "Nazwa sekcji tematycznej",
      "tresc": "Podsumowanie sekcji",
      "cytaty": ["dosłowny cytat 1", "dosłowny cytat 2"]
    }
  ],
  "ustalenia": ["Lista osiągniętych ustaleń i wniosków"],
  "daty_chronologicznie": [
    {"data": "YYYY-MM-DD", "wydarzenie": "Opis wydarzenia"}
  ],
  "kluczowe_daty_podsumowanie": "Podsumowanie wszystkich terminów w jednym miejscu"
}
```

## Zadania Implementacyjnych

### 1. AI Processor (`ai_processor.py`)

Dodaj nową metodę:

```python
def analyze_long_note(self, transcription):
    """
    Dogłębna analiza długiej notatki z uczestnikami, sekcjami, cytatami i chronologią
    """
    # Implementacja z promptem powyżej
    # Zwraca dict z polami: tytul, uczestnicy, sekcje, ustalenia, daty_chronologicznie, kluczowe_daty_podsumowanie
```

### 2. Database Model (`database.py`)

Rozszerz model `Notatka` o nowe pola:

```python
# Pola dla analizy długich notatek
czy_analizowane = Column(Boolean, default=False)
uczestnicy = Column(Text, nullable=True)           # JSON array
sekcje = Column(Text, nullable=True)                # JSON array
cytaty = Column(Text, nullable=True)                # JSON array
ustalenia = Column(Text, nullable=True)             # JSON array
daty_chronologicznie = Column(Text, nullable=True)  # JSON array
podsumowanie_dat = Column(Text, nullable=True)      # TEXT
```

### 3. Nowa migracja bazy danych

Utwórz plik: `migrate_add_long_note_analysis.py`

Dodaje kolumny:
- `czy_analizowane` (BOOLEAN)
- `uczestnicy` (TEXT)
- `sekcje` (TEXT)
- `cytaty` (TEXT)
- `ustalenia` (TEXT)
- `daty_chronologicznie` (TEXT)
- `podsumowanie_dat` (TEXT)

### 4. Bot - nowe stany konwersacji (`bot.py`)

```python
COLLECTING_AUDIO, WAITING_CONFIRMATION, EDITING_TEMAT, EDITING_OPIS,
WAITING_PHOTOS, ASKING_PDF, EDITING_NOTE, ASKING_ANALYSIS = range(8)
```

### 5. Bot - logika detekcji

Po transkrypcji w `handle_voice()` / `handle_audio()`:

```python
transcription, duration = ai.transcribe_audio(audio_file, filename)

if duration > 300:  # 5 minut = 300 sekund
    # Zapytaj użytkownika o analizę
    return ASKING_ANALYSIS
```

### 6. Bot - handler pytania o analizę

```python
async def ask_about_analysis(update, context):
    duration = context.user_data.get('current_duration', 0)

    await update.message.reply_text(
        f"📊 Notatka jest długa: {duration//60} minut.\n\n"
        "Czy przeprowadzić dogłębną analizę z:\n"
        "• identyfikacją uczestników\n"
        "• podziałem na sekcje tematyczne\n"
        "• kluczowymi cytatami\n"
        "• chronologią wydarzeń\n"
        "• listą ustaleń",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Tak, analizuj", callback_data="analysis_yes")],
            [InlineKeyboardButton("❌ Nie, zapisz normalnie", callback_data="analysis_no")]
        ])
    )
    return ASKING_ANALYSIS
```

### 7. Bot - handler wyświetlania analizy

```python
async def send_analysed_note(note, update):
    """Wyświetla notatkę z pełną analizą"""
    # Formatowanie z sekcjami, cytatami, uczestnikami, datami
```

### 8. Web App - aktualizacja widoku

W `templates/notes_list.html` i `web_app.py`:
- Wyświetlaj informację o analizie
- Pokazuj sekcje tematyczne
- Rozwiń chronologię dat

## Format Wyświetlania

```
📊 ANALIZA NOTATKI

📌 Tytuł notatki / Temat spotkania

👥 Uczestnicy: Rozmówca A, Rozmówca B

📋 TREŚĆ:

▫️ Sekcja 1
   Podsumowanie sekcji...

   💬 Cytaty:
      » "dosłowny cytat 1"
      » "dosłowny cytat 2"

▫️ Sekcja 2
   ...

✅ USTALENIA / WNIOSKI:
   • Ustalenie 1
   • Ustalenie 2

📅 CHRONOLOGIA:
   2025-01-20: Spotkanie z klientem
   2025-01-25: Deadline projektu

🗓️ KLUCZOWE DATY I TERMINY:
   Podsumowanie wszystkich terminów w jednym miejscu

────────────────────────────────────
📊 Notatka przeanalizowana (AI)
```

## Szacunkowe Koszty

Dla ~5-minutowej notatki:

| Operacja | Koszt |
|----------|-------|
| Transkrypcja (Whisper) | ~$0.03 |
| Ekstrakcja podstawowa | ~$0.0005 |
| Analiza dogłębna | ~$0.002-0.004 |
| **RAZEM** | **~$0.03-0.04** |

## Decyzje do podjęcia

1. **Próg długości:** 5 minut (300 sekund) - OK?
2. **Model:** gpt-4o-mini czy gpt-4o dla lepszej jakości?
3. **Streszczenie vs Pełna analiza:** Czy dla >10 minut robić tylko streszczenie?
4. **Wyszukiwanie:** Czy wykorzystać sekcje i cytaty do ulepszenia wyszukiwania semantycznego?

## Zależności

- `ai_processor.py` - nowa metoda `analyze_long_note()`
- `database.py` - rozszerzenie modelu `Notatka`
- `bot.py` - nowy stan `ASKING_ANALYSIS` i handlery
- `migrate_add_long_note_analysis.py` - nowa migracja
- `templates/notes_list.html` - aktualizacja UI webowej
