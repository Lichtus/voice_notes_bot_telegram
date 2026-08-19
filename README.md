# 🎙️ Voice Notes Telegram Bot

Bot Telegram, który zamienia notatki głosowe w uporządkowaną treść. Nagranie trafia do
Whispera po transkrypcję, następnie GPT-4o-mini wyciąga z niego temat, opis, zadania,
kluczowe myśli i terminy. Całość ląduje w bazie, którą można przeglądać z poziomu
Telegrama albo w dołączonej aplikacji webowej.

Bot jest napisany pod język polski — prompt wymusza 1. osobę liczby pojedynczej,
usuwa wypełniacze („eeeyy", „yyy") i porządkuje mowę potoczną w zwięzły tekst.

## ✨ Co potrafi

- **Notatki głosowe i pliki audio** — voice message albo wgrany plik (MP3, WAV, M4A, OGG).
  Jedną notatkę można złożyć z kilku nagrań; transkrypcje są sklejane znacznikami `[Część N]`.
- **Automatyczna struktura** — temat, opis, lista zadań, kluczowe myśli, terminy oraz
  kategoria (`Praca` / `Dom` / `Inne`) z oceną pewności klasyfikacji.
- **Dogłębna analiza długich nagrań** — powyżej 5 minut bot proponuje szczegółowy raport:
  identyfikacja rozmówców, podział na sekcje tematyczne z cytatami, lista ustaleń
  i chronologia dat.
- **Zdjęcia i PDF** — do notatki można dołączyć zdjęcia i wygenerować z całości PDF-a.
- **Wyszukiwanie głosowe** — semantyczne, po embeddingach, z procentem dopasowania.
- **Zadania** — lista niewykonanych zadań i oznaczanie ich jako zrobione.
- **Śledzenie kosztów** — koszt Whispera, GPT i embeddingów zapisywany przy każdej notatce.
- **Aplikacja webowa** — przeglądanie notatek, zadań i statystyk w przeglądarce.
- **Whitelist** — z bota korzystają wyłącznie ID wymienione w `ALLOWED_USER_IDS`.

## 📋 Wymagania

- Docker i Docker Compose — albo Python **3.10+**, jeśli wolisz uruchamiać bez kontenerów
- Token bota z [@BotFather](https://t.me/BotFather)
- Klucz API OpenAI
- Własne Telegram User ID (poda je [@userinfobot](https://t.me/userinfobot))

## 🚀 Uruchomienie

### Docker (zalecane)

```bash
git clone https://github.com/Lichtus/voice_notes_bot_telegram.git
cd voice_notes_bot_telegram

cp .env.example .env        # uzupełnij tokeny — patrz niżej
mkdir -p data               # katalog na bazę SQLite

docker compose up -d --build
docker compose logs -f bot  # szukaj: 🚀 Bot uruchomiony!
```

Aplikacja webowa startuje razem z botem pod `http://localhost:5000`.

Przydatne polecenia:

```bash
docker compose logs -f bot      # podgląd logów bota
docker compose restart bot      # restart po zmianie .env
docker compose up -d --build    # przebudowa po zmianie kodu
docker compose down             # zatrzymanie
```

### Bez Dockera

Bot i aplikacja webowa mają rozdzielne zależności i uruchamia się je jako dwa procesy:

```bash
python -m venv venv && source venv/bin/activate

pip install -r requirements-bot.txt && python bot.py
pip install -r requirements-web.txt && python web_app.py
```

Generowanie PDF wymaga bibliotek systemowych WeasyPrint (Pango, Cairo, gdk-pixbuf).
Na Debianie/Ubuntu/Mincie:

```bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 \
                 shared-mime-info fonts-dejavu-core
```

> **Uwaga:** Telegram pozwala tylko jednej instancji odpytywać token. Bot w kontenerze
> i bot z venv nie mogą działać jednocześnie — ten, który przegra, będzie logował
> `409 Conflict`.

### Konfiguracja `.env`

| Zmienna | Wymagana | Opis |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | tak | Token od @BotFather |
| `ALLOWED_USER_IDS` | tak | Lista dozwolonych ID po przecinku, np. `123456789,987654321` |
| `OPENAI_API_KEY` | tak | Klucz API OpenAI |
| `DATABASE_PATH` | nie | Ścieżka pliku SQLite (domyślnie `voice_notes.db`) |
| `DATABASE_URL` | nie | Adres PostgreSQL/Supabase — jeśli ustawiony, wypiera SQLite |
| `WEB_SECRET_KEY` | dla weba | Sekret sesji Flaska |
| `WEB_APP_URL` | dla weba | Adres, pod który bot wysyła kody logowania |

W Dockerze `DATABASE_PATH` i `WEB_APP_URL` są nadpisywane przez `docker-compose.yml`
wartościami właściwymi dla sieci kontenerów — nie trzeba ich ustawiać ręcznie.

## 📱 Komendy

| Komenda | Działanie |
|---|---|
| `/start` | Powitanie i ściąga z komend |
| `/lista` | 10 ostatnich notatek |
| `/ostatnia` | Najnowsza notatka |
| `/notatka [id]` | Pełna notatka wraz z nagraniem |
| `/szukaj [tekst]` | Wyszukiwanie **tekstowe** po temacie, opisie i transkrypcji |
| `/zadania` | Niewykonane zadania |
| `/wykonane [id]` | Oznacz zadanie jako zrobione |
| `/stats` | Statystyki i koszty |

## 🔄 Jak przebiega dodanie notatki

1. Wysyłasz voice message lub plik audio → `🎤 Plik audio otrzymany! Przetwarzam...`
2. Whisper transkrybuje nagranie.
3. Jeśli pierwsze słowo to `szukaj`, `znajdź`, `wyszukaj`, `pokaż`, `search`, `find`
   lub `znajdz` — bot nie tworzy notatki, tylko wyszukuje (patrz niżej).
4. Możesz dołożyć kolejne nagrania (`➕ Dodaj więcej nagrań`) albo przejść dalej
   (`✅ To wszystko - przetwórz`).
5. Przy nagraniu dłuższym niż **5 minut** bot pyta, czy przeprowadzić dogłębną analizę.
6. GPT-4o-mini zwraca strukturę, bot pokazuje podgląd z przyciskami
   `📸 Dodaj zdjęcia` / `⏭️ Pomiń` / `✏️ Edytuj temat` / `❌ Anuluj`.
7. Po zdjęciach bot proponuje wygenerowanie PDF-a.
8. Notatka trafia do bazy razem z embeddingiem i rozpisanymi kosztami.

Istniejącą notatkę można uzupełnić kolejnym nagraniem — przycisk `🎤 Uzupełnij nagraniem`
dokleja nową transkrypcję i przelicza strukturę.

## 🔍 Dwa różne wyszukiwania

Warto je rozróżniać, bo działają zupełnie inaczej:

- **Głosowe — semantyczne.** Powiedz „Szukaj spotkanie z Jankiem". Zapytanie idzie przez
  `text-embedding-3-small`, a bot liczy podobieństwo kosinusowe do embeddingów wszystkich
  notatek i zwraca 5 najlepszych **z procentem dopasowania**. Znajdzie notatkę
  o zbliżonym znaczeniu, nawet bez wspólnych słów.
- **`/szukaj` — tekstowe.** Zwykłe dopasowanie podciągu w temacie, opisie i transkrypcji.
  Bez embeddingów i bez procentów. Znajdzie tylko dokładnie wpisany ciąg znaków.

## 🌐 Aplikacja webowa

Flask pod `http://localhost:5000`, dzielący bazę z botem. Pozwala przeglądać notatki
(z filtrowaniem, sortowaniem i wyszukiwaniem), odhaczać zadania, oglądać statystyki
kosztów i przygotować notatkę do wysłania mailem. Zdjęcia są pobierane na żywo z serwerów
Telegrama — w bazie leżą wyłącznie identyfikatory plików.

Logowanie działa na dwa sposoby: przez widget Telegram Login (weryfikacja HMAC) albo
6-cyfrowym kodem, który bot wysyła po `/start webapp_login`. Kod jest ważny 5 minut
i trzymany w pamięci procesu — restart aplikacji go unieważnia.

## 🗄️ Baza danych

SQLite z włączonym trybem WAL, albo PostgreSQL/Supabase po ustawieniu `DATABASE_URL`.
Dwie tabele — źródłem prawdy dla schematu jest `database.py`:

**`notatki`** — 31 kolumn w kilku grupach:

| Grupa | Kolumny |
|---|---|
| Podstawowe | `id`, `telegram_user_id`, `data_utworzenia`, `temat`, `opis`, `transkrypcja` |
| Załączniki | `audio_file_id`, `photo_file_ids` (JSON) |
| Struktura | `kategoria`, `kluczowe_mysli`, `terminy`, `auto_category_confidence` |
| Wyszukiwanie | `embedding` (JSON z wektorem 1536 wymiarów) |
| Koszty | `audio_duration_seconds`, `tokens_*`, `cost_*_usd`, `processing_time` |
| Dogłębna analiza | `czy_analizowane`, `analiza_tytul`, `analiza_uczestnicy`, `analiza_sekcje`, `analiza_ustalenia`, `analiza_daty_chronologicznie`, `analiza_podsumowanie_dat` |
| Kasowanie | `deleted_at` |

**`zadania`** — `id`, `notatka_id`, `zadanie`, `wykonane`, `data_wykonania`.

Dwie decyzje projektowe, które łatwo przeoczyć:

- **Miękkie usuwanie.** Notatki nigdy nie znikają z bazy — kasowanie ustawia `deleted_at`,
  a wszystkie odczyty filtrują po `deleted_at IS NULL`.
- **Koszty jako TEXT.** Kwoty rzędu ułamków centa gubiłyby precyzję w kolumnach `REAL`,
  dlatego trzymane są jako tekst.

Świeża baza powstaje sama przy pierwszym starcie — `Base.metadata.create_all()` zakłada
tabele od razu z pełnym schematem. Uwaga: nie dodaje natomiast kolumn do tabel, które już
istnieją, więc podniesienie bazy założonej na starszej wersji modelu wymaga ręcznego
`ALTER TABLE`. Historyczne skrypty migracyjne leżą poza repozytorium.

## 💰 Koszty OpenAI

| Składnik | Stawka |
|---|---|
| Whisper | $0.006 / minutę nagrania |
| GPT-4o-mini | $0.15 / 1M tokenów wejścia, $0.60 / 1M wyjścia |
| text-embedding-3-small | $0.02 / 1M tokenów |

W praktyce sama strukturyzacja krótkiej notatki kosztuje ok. **$0.0002**; rachunek robi
transkrypcja. Przy 50 notatkach po 2 minuty wychodzi ok. **$0.60/miesiąc**.

Stawki są zapisane na sztywno w `cost_calculator.py` (stan na grudzień 2025) — przy zmianie
modelu trzeba je zaktualizować, inaczej historyczne koszty przestaną się zgadzać.

## 📂 Struktura projektu

```
voice_notes_bot_telegram/
├── bot.py                  # Bot Telegram — handlery i przepływy konwersacji
├── web_app.py              # Aplikacja webowa (Flask)
├── ai_processor.py         # Whisper, GPT, embeddingi
├── cost_calculator.py      # Przeliczanie zużycia API na dolary
├── database.py             # Modele i dostęp do bazy (SQLAlchemy)
├── config.py               # Konfiguracja i prompty GPT
├── templates/              # Szablony HTML aplikacji webowej
├── static/                 # Style
├── Dockerfile              # Obraz wielostopniowy: targety bot i web
├── docker-compose.yml      # Definicja obu usług
├── requirements-bot.txt    # Zależności bota
├── requirements-web.txt    # Zależności aplikacji webowej
├── migrate_to_supabase.py  # Przeniesienie danych z SQLite do PostgreSQL
├── view_database.py        # Przeglądarka bazy z linii poleceń
└── data/                   # Baza SQLite (wolumen Dockera)
```

Opis architektury dla asystentów AI: `CLAUDE.md`.

## 🔒 Bezpieczeństwo

- **Whitelist.** Dekorator `@check_user_allowed` chroni wszystkie komendy oraz wejście
  na ścieżkę audio, więc obcy użytkownik nie rozpocznie żadnego przepływu. Handler
  przycisków inline (`button_handler`) nie ma osobnej weryfikacji — jest osiągalny
  dopiero z klawiatury, którą bot wysyła autoryzowanej osobie, a wszystkie zapytania
  do bazy i tak filtrują po `telegram_user_id`. Dodanie dekoratora także tam byłoby
  jednak porządniejsze.
- **Sekrety w `.env`.** Plik jest w `.gitignore` i nie trafia do obrazu Dockera;
  kontenery dostają go przez `env_file` dopiero przy starcie.
- **Port tylko lokalnie.** `docker-compose.yml` wystawia aplikację webową na
  `127.0.0.1:5000`, ponieważ widoki `/notes`, `/tasks` i `/statistics` **nie mają
  jeszcze kontroli logowania**. Zanim udostępnisz ją w sieci, dopisz autoryzację.

## 🐛 Rozwiązywanie problemów

**`telegram.error.Conflict: terminated by other getUpdates request`**
Działa druga instancja bota na tym samym tokenie. Sprawdź `docker compose ps` oraz
`systemctl is-active voice-notes-bot` i zostaw tylko jedną.

**`openai.AuthenticationError: 401`**
Klucz jest nieważny lub należy do innego projektu. Podmień `OPENAI_API_KEY` w `.env`
i zrób `docker compose up -d bot` — przebudowa nie jest potrzebna.

**Bot nie odpowiada**
`docker compose logs -f bot`, a bez Dockera `ps aux | grep bot.py`. Upewnij się, że Twoje
Telegram User ID faktycznie jest w `ALLOWED_USER_IDS`.

**Brak uprawnień do katalogu `data/`**
Kontenery działają jako uid/gid 1000. Jeśli `data/` powstał jako własność roota
(bo Docker utworzył go automatycznie), napraw to: `sudo chown -R 1000:1000 data`.

## 🗺️ Plany

- [ ] Przypomnienia o zadaniach z terminem
- [ ] Kontrola logowania na wszystkich widokach aplikacji webowej
- [ ] Odczyt rzeczywistej długości nagrania zamiast szacowania z rozmiaru pliku
- [ ] Obsługa innych języków niż polski
- [ ] Weryfikacja whitelisty również w handlerze przycisków inline

## 📄 Licencja

MIT.
