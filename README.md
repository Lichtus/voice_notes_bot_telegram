# 🎙️ Voice Notes Telegram Bot

Bot Telegram do automatycznego przetwarzania notatek głosowych z wykorzystaniem AI (OpenAI Whisper + GPT-4o-mini).

## ✨ Funkcje

- 🎤 **Nagrywanie głosowe** - wyślij voice message, bot automatycznie przetworzy
- 🎵 **Pliki audio** - wgraj pliki audio (MP3, WAV, M4A, OGG, WEBM) - wszystkie obsługiwane!
- 🤖 **AI Processing** - automatyczna transkrypcja (Whisper) i ekstrakcja struktury (GPT-4o-mini)
- 📋 **Struktura notatek**:
  - Temat (automatycznie wykrywany)
  - Opis (pełna treść)
  - Zadania do zrobienia (automatycznie wyodrębniane)
- 💾 **Baza SQLite** - wszystkie notatki zapisywane lokalnie
- 🔍 **Wyszukiwanie semantyczne** - głosowe i tekstowe wyszukiwanie z % dopasowania
- ✅ **Zarządzanie zadaniami** - lista zadań i oznaczanie jako wykonane
- 🔒 **Bezpieczeństwo** - whitelist użytkowników (tylko Ty masz dostęp)

## 📋 Wymagania

- Python 3.9+
- Telegram Bot Token (z @BotFather)
- OpenAI API Key
- Twój Telegram User ID

## 🚀 Instalacja (Lokalna)

### 1. Sklonuj repozytorium

```bash
git clone <repo-url>
cd 25_wrozenia_aplikacji_notatki
```

### 2. Zainstaluj zależności

```bash
pip install -r requirements-bot.txt
```

### 3. Utwórz bota w Telegram

1. Otwórz [@BotFather](https://t.me/BotFather) w Telegram
2. Wyślij `/newbot`
3. Podaj nazwę i username bota
4. **Zapisz TOKEN** który otrzymasz

### 4. Znajdź swój Telegram User ID

Możesz użyć bota [@userinfobot](https://t.me/userinfobot) - wyślij `/start` i otrzymasz swój ID.

### 5. Skonfiguruj zmienne środowiskowe

Skopiuj `.env.example` do `.env`:

```bash
cp .env.example .env
```

Edytuj `.env` i uzupełnij:

```env
TELEGRAM_BOT_TOKEN=twoj_bot_token_tutaj
ALLOWED_USER_IDS=twoj_user_id_tutaj
OPENAI_API_KEY=twoj_openai_api_key_tutaj
DATABASE_PATH=voice_notes.db
```

**WAŻNE:** Jeśli chcesz dać dostęp wielu osobom, wpisz ID oddzielone przecinkami:
```env
ALLOWED_USER_IDS=123456789,987654321
```

### 6. Uruchom bota

```bash
python bot.py
```

Powinieneś zobaczyć:
```
🚀 Bot uruchomiony!
```

### 7. Testuj bota

1. Otwórz Telegram i znajdź swojego bota
2. Wyślij `/start`
3. Wyślij voice message
4. Bot automatycznie przetworzy i wyświeci strukturę notatki!

## 📱 Jak używać

### Komendy

- `/start` - Rozpocznij i zobacz instrukcje
- `/lista` - Pokaż ostatnie 10 notatek
- `/szukaj [słowo]` - Wyszukaj notatki po słowach kluczowych
- `/zadania` - Pokaż wszystkie niewykonane zadania
- `/wykonane [id]` - Oznacz zadanie jako wykonane
- `/stats` - Statystyki (liczba notatek, zadań, itp.)

### Workflow dodawania notatki

1. **Wyślij voice message** na czat z botem
2. Bot odpowiada: "🎤 Nagranie otrzymane! Przetwarzam..."
3. Bot transkrybuje przez **Whisper**
4. Bot analizuje przez **GPT-4o-mini** i wyciąga:
   - 📌 Temat
   - 📝 Opis
   - ✅ Zadania do zrobienia
5. Bot pokazuje podgląd:
   ```
   ✅ Notatka przetworzona!

   📌 TEMAT:
   Zakupy i spotkanie z Jankiem

   📝 OPIS:
   Kupić mleko, chleb, masło. Spotkanie z Jankiem jutro o 15:00

   📋 ZADANIA:
   1. Zadzwonić do dentysty
   2. Wysłać maila do szefa

   💾 Zapisać tę notatkę?
   [✅ Zapisz] [✏️ Edytuj temat] [❌ Anuluj]
   ```
6. Kliknij **✅ Zapisz** lub edytuj temat

## 🗄️ Struktura bazy danych

### Tabela: `notatki`

| Kolumna | Typ | Opis |
|---------|-----|------|
| id | INTEGER | Klucz główny |
| telegram_user_id | INTEGER | ID użytkownika Telegram |
| data_utworzenia | TIMESTAMP | Data i czas utworzenia |
| temat | VARCHAR(255) | Tytuł notatki |
| opis | TEXT | Szczegółowy opis |
| transkrypcja | TEXT | Pełna transkrypcja audio |
| audio_file_id | TEXT | ID pliku audio w Telegram |

### Tabela: `zadania`

| Kolumna | Typ | Opis |
|---------|-----|------|
| id | INTEGER | Klucz główny |
| notatka_id | INTEGER | Klucz obcy do notatki |
| zadanie | TEXT | Treść zadania |
| wykonane | BOOLEAN | Czy wykonane |
| data_wykonania | TIMESTAMP | Kiedy wykonano |

## 🌐 Deployment na Google Cloud (f1-micro - DARMOWY)

Zobacz szczegółową instrukcję w pliku: **[GOOGLE_CLOUD_SETUP.md](GOOGLE_CLOUD_SETUP.md)**

**Skrócona wersja:**

1. Załóż konto Google Cloud (free tier)
2. Utwórz f1-micro VM (region us-west1/us-central1/us-east1)
3. Zaloguj się przez SSH
4. Zainstaluj Python i zależności
5. Skopiuj kod bota
6. Skonfiguruj `.env`
7. Uruchom bota w tle (systemd lub screen)

**Koszt: $0/miesiąc** (w ramach free tier)

## 💰 Koszty OpenAI API

- **Whisper**: ~$0.006 za minutę nagrania
- **GPT-4o-mini**: ~$0.0001-0.0002 za notatkę

**Szacunkowy koszt:** 50 notatek/miesiąc = **~$1-2/miesiąc**

## 📂 Struktura projektu

```
25_wrozenia_aplikacji_notatki/
├── bot.py                  # Główny plik bota
├── config.py               # Konfiguracja
├── database.py             # Logika bazy danych (SQLAlchemy)
├── ai_processor.py         # OpenAI Whisper + GPT
├── requirements-bot.txt    # Zależności Python
├── .env.example            # Przykładowa konfiguracja
├── .gitignore              # Ignorowane pliki
├── README.md               # Ten plik
├── GOOGLE_CLOUD_SETUP.md   # Instrukcja deployment na GCP
└── voice_notes.db          # Baza SQLite (tworzona automatycznie)
```

## 🔒 Bezpieczeństwo

1. **Whitelist użytkowników**: Tylko osoby z ID w `ALLOWED_USER_IDS` mają dostęp
2. **Zmienne środowiskowe**: Wszystkie sekrety w `.env` (nigdy nie commituj!)
3. **SQLite lokalnie**: Baza tylko na Twoim serwerze
4. **HTTPS**: Telegram API używa szyfrowania

## 🐛 Troubleshooting

### Bot nie odpowiada

1. Sprawdź czy bot jest uruchomiony: `ps aux | grep bot.py`
2. Sprawdź logi w terminalu
3. Sprawdź czy User ID jest w `ALLOWED_USER_IDS`

### Błąd "TELEGRAM_BOT_TOKEN nie jest ustawiony"

Sprawdź czy plik `.env` istnieje i ma poprawny token.

### Błąd OpenAI API

1. Sprawdź czy `OPENAI_API_KEY` jest poprawny
2. Sprawdź czy masz środki na koncie OpenAI
3. Sprawdź limity API: https://platform.openai.com/usage

### Baza danych nie działa

Sprawdź uprawnienia do katalogu (bot musi móc tworzyć plik `.db`):
```bash
chmod 755 .
```

## 📝 TODO (Przyszłe funkcje)

- [ ] Eksport notatek do PDF/Markdown
- [ ] Przypomnienia o zadaniach (notifications)
- [ ] Kategorie/tagi dla notatek
- [ ] Multi-language support
- [ ] Web dashboard (Flask/FastAPI)

## 🤝 Kontakt

Masz pytania? Otwórz issue na GitHubie!

## 📄 Licencja

MIT License - używaj jak chcesz! 🎉
