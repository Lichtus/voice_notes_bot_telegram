# 📸📄 Aktualizacja: Zdjęcia i PDF w Notatkach

Przewodnik aktualizacji Voice Notes Bot o funkcje załączników zdjęciowych i generowania PDF.

**Nowe funkcje:**
- ✅ Załączanie zdjęć do notatek
- ✅ Generowanie sformatowanych PDF z notatkami
- ✅ Osadzanie zdjęć w PDF
- ✅ Elegancki design PDF (HTML → PDF)

**Czas aktualizacji: 10-15 minut**

---

## 🎯 Nowy Workflow Tworzenia Notatki

### Przed Aktualizacją:
1. Wysłanie voice message → AI przetwarza → Zapisanie

### Po Aktualizacji:
1. Wysłanie voice message
2. AI przetwarza (temat, opis, zadania)
3. **Bot pyta: "Czy chcesz dodać zdjęcia?"**
   - 📸 Dodaj zdjęcia → Wyślij zdjęcia → Zakończ dodawanie
   - ⏭️ Pomiń
4. **Bot pyta: "Czy chcesz wygenerować PDF?"**
   - 📄 Tak, generuj PDF → Bot generuje i wysyła PDF
   - ⏭️ Nie, zapisz bez PDF
5. Notatka zapisana w bazie (z zdjęciami jeśli były)

---

## CZĘŚĆ 1: Aktualizacja Kodu na Linux Mint (5-7 minut)

### Krok 1: Pobierz Najnowszy Kod z GitHub

```bash
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram

# Sprawdź obecny branch
git branch

# Jeśli jesteś na main, przełącz się na feature branch
git fetch origin
git checkout claude/voice-notes-app-design-9rEYp

# Lub jeśli zmiany są już na main:
git checkout main
git pull origin main
```

### Krok 2: Zainstaluj Nowe Zależności

WeasyPrint wymaga dodatkowych bibliotek systemowych (dla renderowania HTML → PDF):

```bash
# Zainstaluj system dependencies dla WeasyPrint
sudo apt update
sudo apt install -y python3-pip python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0

# Aktywuj venv
source venv/bin/activate

# Zainstaluj nowe Python packages
pip install --upgrade pip
pip install weasyprint==60.2

# Jeśli masz problemy, spróbuj:
pip install --no-cache-dir weasyprint

# Sprawdź czy zainstalowane
python -c "import weasyprint; print('✅ WeasyPrint OK')"

# Deaktywuj venv
deactivate
```

**Troubleshooting WeasyPrint:**

Jeśli `pip install weasyprint` zawiedzie, zainstaluj dependencies:

```bash
# Dla Ubuntu/Linux Mint:
sudo apt install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info

# Następnie ponów instalację
source venv/bin/activate
pip install weasyprint
deactivate
```

### Krok 3: Restart Bota

```bash
# Zatrzymaj
sudo systemctl stop voice-notes-bot

# Uruchom
sudo systemctl start voice-notes-bot

# Sprawdź status
sudo systemctl status voice-notes-bot

# Sprawdź logi
sudo journalctl -u voice-notes-bot -n 30 --no-pager
```

**Szukaj w logach:**
```
💾 Używam bazy danych: SQLite (voice_notes.db)
🚀 Bot uruchomiony!
```

Jeśli widzisz błędy o brakujących modułach - sprawdź czy venv jest poprawnie skonfigurowany w systemd service.

---

## CZĘŚĆ 2: Test Nowych Funkcji (5 minut)

### Test 1: Notatka z Zdjęciami (Bez PDF)

1. Otwórz bota w Telegram
2. Wyślij **voice message**: _"Testowa notatka z zdjęciami"_
3. Bot przetworzy i zapyta: **"Czy chcesz dodać zdjęcia?"**
4. Kliknij: **📸 Dodaj zdjęcia**
5. Wyślij **2-3 zdjęcia** (dowolne)
6. Kliknij: **✅ Zakończ dodawanie zdjęć**
7. Bot zapyta: **"Czy chcesz wygenerować PDF?"**
8. Kliknij: **⏭️ Nie, zapisz bez PDF**
9. Bot zapisze notatkę z załączonymi zdjęciami ✅

### Test 2: Notatka z PDF (Bez Zdjęć)

1. Wyślij voice message: _"Lista zakupów: mleko, chleb, masło"_
2. Bot zapyta o zdjęcia → Kliknij: **⏭️ Pomiń**
3. Bot zapyta o PDF → Kliknij: **📄 Tak, generuj PDF**
4. Bot wygeneruje i wyśle **PDF** z notatką! 🎉

### Test 3: Pełna Funkcjonalność (Zdjęcia + PDF)

1. Wyślij voice message: _"Spotkanie z klientem - omówić budżet, podpisać umowę"_
2. Bot przetworzy → Dodaj zdjęcia → Kliknij: **📸 Dodaj zdjęcia**
3. Wyślij kilka zdjęć (np. zdjęcia z tablicy, dokumenty)
4. Kliknij: **✅ Zakończ dodawanie**
5. Bot zapyta o PDF → Kliknij: **📄 Tak, generuj PDF**
6. Bot wygeneruje **PDF z osadzonymi zdjęciami!** 🎉

Pobierz PDF z Telegram i otwórz - powinieneś zobaczyć:
- Pięknie sformatowaną notatkę
- Temat, opis, zadania
- Zdjęcia osadzone w PDF

---

## 🗃️ Baza Danych - Co się Zmieniło?

### Nowa Kolumna w Tabeli `notatki`:

```sql
photo_file_ids TEXT  -- JSON array z Telegram file_id zdjęć
```

**Migracja automatyczna!** SQLAlchemy samo doda kolumnę przy pierwszym uruchomieniu.

### Sprawdź Bazę Danych:

```bash
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram
source venv/bin/activate

# Sprawdź strukturę bazy
sqlite3 voice_notes.db ".schema notatki"

# Powinieneś zobaczyć:
# ...
# photo_file_ids TEXT
# ...

# Sprawdź notatki z zdjęciami
sqlite3 voice_notes.db "SELECT id, temat, photo_file_ids FROM notatki WHERE photo_file_ids IS NOT NULL;"

deactivate
```

---

## 📊 Przykładowy PDF - Co Jest Wewnątrz?

PDF generowany przez bota zawiera:

```
┌─────────────────────────────────────┐
│     📝 Notatka #42                  │
│     📅 2024-12-28 14:30:00          │
├─────────────────────────────────────┤
│                                     │
│  📌 Temat                           │
│  Spotkanie z klientem               │
│                                     │
│  📝 Opis                            │
│  Omówienie budżetu projektu...      │
│                                     │
│  📋 Zadania                         │
│  ☐ Omówić budżet                    │
│  ☐ Podpisać umowę                   │
│                                     │
│  📸 Zdjęcia                         │
│  [Zdjęcie 1 - osadzone]             │
│  [Zdjęcie 2 - osadzone]             │
│                                     │
├─────────────────────────────────────┤
│  Wygenerowano przez Voice Notes Bot │
└─────────────────────────────────────┘
```

**Style CSS:**
- Kolorowe sekcje (zielony header, niebieskie nagłówki)
- Zadania ze żółtym tłem i checkboxami
- Zdjęcia z zaokrąglonymi rogami i cieniami
- Format A4 z marginesami 2cm

---

## 🐛 Troubleshooting

### Błąd: "ModuleNotFoundError: No module named 'weasyprint'"

**Przyczyna:** WeasyPrint nie jest zainstalowany w venv.

**Rozwiązanie:**
```bash
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram
source venv/bin/activate
pip install weasyprint
deactivate
sudo systemctl restart voice-notes-bot
```

### Błąd: "OSError: cannot load library 'gobject-2.0-0'"

**Przyczyna:** Brakuje system dependencies.

**Rozwiązanie:**
```bash
sudo apt update
sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0
sudo systemctl restart voice-notes-bot
```

### Błąd: "cairo.Error: no memory"

**Przyczyna:** Zdjęcia są za duże lub za dużo zdjęć.

**Rozwiązanie:** Telegram automatycznie kompresuje zdjęcia, więc ten błąd jest rzadki. Jeśli występuje:
- Ogranicz do max 5 zdjęć na notatkę
- Kod automatycznie używa skompresowanej wersji zdjęć z Telegram

### PDF generuje się, ale zdjęcia nie widać

**Przyczyna:** Błąd pobierania zdjęć z Telegram lub konwersji base64.

**Sprawdź logi:**
```bash
sudo journalctl -u voice-notes-bot -n 100 | grep "Błąd pobierania zdjęcia"
```

**Rozwiązanie:** Sprawdź czy bot ma dostęp do internetu i czy Telegram file_id jest ważny.

### Bot działa, ale nie pyta o zdjęcia/PDF

**Przyczyna:** Stary kod w pamięci lub błędny branch.

**Rozwiązanie:**
```bash
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram

# Sprawdź branch
git branch

# Sprawdź czy masz najnowszy kod
git log -1 --oneline

# Restart bota
sudo systemctl restart voice-notes-bot
sudo journalctl -u voice-notes-bot -n 20
```

---

## 🎨 Dostosowywanie PDF

Jeśli chcesz zmienić wygląd PDF, edytuj funkcję `generate_pdf()` w `bot.py`:

### Zmiana Kolorów:

```python
# Znajdź w bot.py (linia ~910):
.header h1 {
    color: #4CAF50;  # ← Zmień na inny kolor (np. #FF5722 - pomarańczowy)
}

h2 {
    color: #2196F3;  # ← Zmień kolor nagłówków sekcji
}
```

### Zmiana Czcionki:

```python
# Znajdź w bot.py (linia ~900):
body {
    font-family: 'DejaVu Sans', Arial, sans-serif;  # ← Zmień czcionkę
}
```

**Dostępne czcionki w WeasyPrint:**
- DejaVu Sans (domyślna)
- DejaVu Serif
- Liberation Sans
- Liberation Serif

### Zmiana Rozmiaru Strony:

```python
# Znajdź w bot.py (linia ~897):
@page {
    size: A4;  # ← Zmień na: Letter, A5, landscape, itp.
    margin: 2cm;  # ← Zmień marginesy
}
```

Po zmianach - **restart bota**:
```bash
sudo systemctl restart voice-notes-bot
```

---

## 📋 Podsumowanie Zmian w Kodzie

| Plik | Co się Zmieniło |
|------|-----------------|
| **bot.py** | • Dodano stany: `WAITING_PHOTOS`, `ASKING_PDF`<br>• Dodano funkcje: `ask_for_photos()`, `handle_photo()`, `ask_for_pdf()`, `generate_pdf()`<br>• Zmieniono `show_note_preview()` - pyta o zdjęcia<br>• Rozszerzono `button_handler()` - obsługa foto/PDF<br>• Zaktualizowano `ConversationHandler` |
| **database.py** | • Dodano kolumnę: `photo_file_ids` (Text/JSON)<br>• Zaktualizowano `add_notatka()` - przyjmuje `photo_file_ids` |
| **requirements-bot.txt** | • Dodano: `weasyprint==60.2` |

---

## 🎉 Gratulacje!

Masz teraz:
- ✅ Bot z obsługą załączników zdjęciowych
- ✅ Generator pięknych PDF z notatkami
- ✅ Zdjęcia osadzone w PDF
- ✅ Elastyczny workflow (zdjęcia opcjonalne, PDF opcjonalny)

**Testuj i ciesz się nowymi funkcjami!** 🚀

---

## 📚 Następne Kroki (Opcjonalne)

Pomysły na dalszy rozwój:
1. **Email notifications** - wysyłaj PDF notatek mailem
2. **Cloud storage** - auto-upload PDF do Google Drive / Dropbox
3. **OCR** - wyciągaj tekst ze zdjęć i dodawaj do notatki
4. **Tags** - tagowanie notatek (praca, osobiste, pomysły)
5. **Przypomnienia** - bot przypomina o zadaniach

---

**Autor:** Voice Notes Bot System
**Data:** 2024-12-28
**Wersja:** 2.0 - Photo Attachments & PDF Generation
