# 🌐 Setup Supabase - Zewnętrzna Baza Danych

Przewodnik integracji Voice Notes Bot z Supabase PostgreSQL (darmowa baza danych w chmurze).

**Czas instalacji: 15-20 minut**

---

## 🎯 Dlaczego Supabase?

- ✅ **CAŁKOWICIE DARMOWE** (500 MB storage, 50,000 użytkowników)
- ✅ **Zarządzana PostgreSQL** w chmurze
- ✅ **Automatyczne backupy**
- ✅ **Web Dashboard** - przeglądaj notatki w przeglądarce
- ✅ **Dane w chmurze** - dostępne nawet gdy laptop wyłączony
- ✅ **Bezpieczeństwo** - szyfrowanie, SSL

---

## CZĘŚĆ 1: Utworzenie Konta Supabase (5 minut)

### Krok 1: Rejestracja

1. Otwórz: **https://supabase.com**
2. Kliknij **Start your project**
3. Zaloguj się przez:
   - **GitHub** (najszybsze, zalecane)
   - lub Email

4. Potwierdź email jeśli używasz email (sprawdź skrzynkę)

### Krok 2: Utwórz Projekt

1. W dashboard kliknij **New Project** (lub **+ New project**)

2. Wypełnij formularz:
   - **Name:** `voice-notes-bot` (lub inna nazwa)
   - **Database Password:** Ustaw **SILNE** hasło
     - Użyj generatora: kliknij 🎲 (generate)
     - **ZAPISZ TO HASŁO!** (skopiuj do notatnika)
   - **Region:** Wybierz najbliższy:
     - `Europe (Frankfurt)` - Niemcy
     - `Europe (London)` - UK
     - `Europe Central (Warsaw)` - Polska (jeśli dostępne)
   - **Pricing Plan:** **Free** (już zaznaczone)

3. Kliknij **Create new project**

⏰ **Czekaj 2-3 minuty** - Supabase tworzy bazę danych

### Krok 3: Pobierz Connection String

Gdy projekt będzie gotowy (zielony status):

1. W lewym menu kliknij **⚙️ Project Settings**
2. Kliknij **Database** (w sekcji Configuration)
3. Przewiń do **Connection string**
4. Wybierz zakładkę **URI**
5. **Skopiuj** connection string:
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```

6. **ZASTĄP `[YOUR-PASSWORD]`** hasłem z Kroku 2!

**Przykład:**
```
postgresql://postgres.abcdefghijklmnop:moje_super_haslo_123@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

**ZAPISZ** ten connection string! Będzie potrzebny w następnym kroku.

---

## CZĘŚĆ 2: Konfiguracja na Linux Mint (10 minut)

### Krok 1: Zainstaluj PostgreSQL Driver

Otwórz terminal:

```bash
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram

# Aktywuj venv
source venv/bin/activate

# Zainstaluj psycopg2 (driver PostgreSQL)
pip install psycopg2-binary

# Deaktywuj
deactivate
```

### Krok 2: Dodaj Connection String do .env

```bash
nano ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram/.env
```

**Dodaj na końcu pliku:**

```env
# Supabase PostgreSQL
DATABASE_URL=postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

**Wklej swój connection string z CZĘŚCI 1, Krok 3!**

**Zapisz:** Ctrl+X → Y → Enter

### Krok 3: Zatrzymaj Bota (Ważne!)

```bash
sudo systemctl stop voice-notes-bot
```

---

## CZĘŚĆ 3: Migracja Danych (5 minut)

### Opcja A: Masz Już Notatki w SQLite (Migruj Dane)

```bash
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram

# Aktywuj venv
source venv/bin/activate

# Uruchom skrypt migracji
python migrate_to_supabase.py
```

**Skrypt:**
- Połączy się z SQLite (stara baza)
- Połączy się z Supabase (nowa baza)
- Skopiuje wszystkie notatki i zadania
- Pokaże progress

**Spodziewany output:**
```
🔄 Migracja danych z SQLite do Supabase

📂 Otwieram SQLite: voice_notes.db
🌐 Łączę z Supabase...

📝 Znaleziono 15 notatek w SQLite

✅ 1/15: Spotkanie z klientem...
✅ 2/15: Lista zakupów...
...
✅ 15/15: Pomysły na projekt...

🎉 Sukces! Zmigrowano 15 notatek do Supabase

📊 Podsumowanie:
   📝 Wszystkich notatek w Supabase: 15
   📋 Wszystkich zadań w Supabase: 23

✅ Migracja zakończona!
```

```bash
# Deaktywuj venv
deactivate
```

### Opcja B: Nowa Instalacja (Bez Danych)

Pomiń migrację - bot automatycznie utworzy puste tabele w Supabase przy pierwszym uruchomieniu.

---

## CZĘŚĆ 4: Test i Uruchomienie (5 minut)

### Krok 1: Uruchom Bota

```bash
sudo systemctl start voice-notes-bot
```

### Krok 2: Sprawdź Logi

```bash
sudo journalctl -u voice-notes-bot -n 30
```

**Szukaj linii:**
```
💾 Używam bazy danych: PostgreSQL (Supabase)
```

Jeśli widzisz tę linię - **sukces!** Bot używa Supabase! ✅

### Krok 3: Testuj w Telegram

1. Wyślij `/start` do bota
2. Nagraj voice message lub wyślij plik audio
3. Bot powinien utworzyć notatkę

### Krok 4: Sprawdź w Supabase Dashboard

1. Otwórz: https://supabase.com/dashboard
2. Wybierz swój projekt
3. W lewym menu kliknij **🗄️ Table Editor**
4. Kliknij tabelę **notatki**
5. **Powinieneś zobaczyć swoją notatkę!** 🎉

---

## 🎉 GOTOWE! Bot Używa Supabase!

**Co się zmieniło:**
- ✅ Dane są teraz w chmurze (Supabase)
- ✅ Automatyczne backupy przez Supabase
- ✅ Możesz przeglądać notatki w przeglądarce
- ✅ Bot nadal działa na Linux Mint
- ✅ Dane dostępne nawet gdy laptop wyłączony

---

## 🔄 Powrót do SQLite (Jeśli Chcesz)

Jeśli z jakiegoś powodu chcesz wrócić do lokalnego SQLite:

```bash
# 1. Zatrzymaj bota
sudo systemctl stop voice-notes-bot

# 2. Zakomentuj DATABASE_URL w .env
nano ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram/.env

# Zmień:
# DATABASE_URL=postgresql://... → #DATABASE_URL=postgresql://...
# (dodaj # na początku linii)

# 3. Zapisz i uruchom bota
sudo systemctl start voice-notes-bot

# 4. Sprawdź logi
sudo journalctl -u voice-notes-bot -n 10
# Powinieneś zobaczyć: "💾 Używam bazy danych: SQLite"
```

Bot automatycznie wróci do SQLite!

---

## 📊 Przeglądanie Danych w Supabase

### Web Dashboard

1. Otwórz: https://supabase.com/dashboard
2. Wybierz projekt `voice-notes-bot`
3. **Table Editor** → `notatki` - zobacz wszystkie notatki
4. **Table Editor** → `zadania` - zobacz wszystkie zadania

**Możesz:**
- ✅ Przeglądać notatki
- ✅ Szukać po tekście
- ✅ Filtrować po dacie
- ✅ Edytować notatki (ostrożnie!)
- ✅ Eksportować do CSV

### SQL Editor (Zaawansowane)

1. **SQL Editor** w Supabase Dashboard
2. Przykładowe zapytania:

```sql
-- Wszystkie notatki z ostatniego tygodnia
SELECT * FROM notatki
WHERE data_utworzenia > NOW() - INTERVAL '7 days'
ORDER BY data_utworzenia DESC;

-- Statystyki
SELECT
  COUNT(*) as total_notes,
  COUNT(DISTINCT telegram_user_id) as unique_users
FROM notatki;

-- Notatki z zadaniami
SELECT n.temat, COUNT(z.id) as liczba_zadan
FROM notatki n
LEFT JOIN zadania z ON n.id = z.notatka_id
GROUP BY n.id, n.temat
ORDER BY liczba_zadan DESC;
```

---

## 🔒 Bezpieczeństwo

### Co Jest Bezpieczne

- ✅ **Szyfrowanie SSL** - cały ruch zaszyfrowany
- ✅ **Hasło do bazy** - tylko Ty znasz
- ✅ **Row Level Security** - Supabase ma wbudowane RLS
- ✅ **Backupy** - automatyczne przez Supabase

### Rekomendacje

1. **Nie udostępniaj DATABASE_URL!**
   - Zawiera hasło do bazy
   - Nie commituj do Git (już w .gitignore)

2. **Użyj silnego hasła**
   - Minimum 16 znaków
   - Litery, cyfry, znaki specjalne

3. **Regularnie sprawdzaj Dashboard**
   - Supabase → Project Settings → Database
   - Sprawdź "Database Health"

4. **Backup .env lokalnie**
   - Zapisz .env w bezpiecznym miejscu
   - Jeśli stracisz DATABASE_URL, stracisz dostęp!

---

## 💰 Koszty - FREE TIER

| Zasób | Limit Free Tier | Twoje Użycie | Koszt |
|-------|-----------------|--------------|-------|
| **Database Size** | 500 MB | ~1-10 MB | $0 |
| **Bandwidth** | 5 GB | ~10-50 MB | $0 |
| **API Requests** | 50,000/mies | ~1,000/mies | $0 |
| **Auth Users** | 50,000 | 1 (Ty) | $0 |
| **TOTAL** | | | **$0/mies** ✅ |

**Szacunki dla 1000 notatek:**
- Database size: ~5-10 MB
- Bandwidth: ~20 MB/mies
- **Całkowicie w FREE TIER!**

**Kiedy trzeba płacić?**
- Przekroczysz 500 MB (bardzo dużo notatek!)
- Przekroczysz 5 GB bandwidth (bardzo duży ruch)
- Wtedy: ~$25/miesiąc (Pro Plan)

---

## 🐛 Troubleshooting

### Bot nie uruchamia się po konfiguracji

**Sprawdź logi:**
```bash
sudo journalctl -u voice-notes-bot -n 50
```

**Częste błędy:**

**1. "connection refused"**
```
Błąd: Connection refused
```

**Rozwiązanie:** Sprawdź czy connection string jest poprawny:
```bash
cat ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram/.env | grep DATABASE_URL
```

Powinien zawierać:
- `postgresql://`
- Twoje hasło (nie `[YOUR-PASSWORD]`)
- Właściwy host Supabase

**2. "password authentication failed"**
```
Błąd: password authentication failed
```

**Rozwiązanie:** Hasło w DATABASE_URL jest błędne. Popraw w .env.

**3. "psycopg2 module not found"**
```
ModuleNotFoundError: No module named 'psycopg2'
```

**Rozwiązanie:**
```bash
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram
source venv/bin/activate
pip install psycopg2-binary
deactivate
sudo systemctl restart voice-notes-bot
```

### Bot używa SQLite zamiast Supabase

**Sprawdź logi:**
```bash
sudo journalctl -u voice-notes-bot -n 20 | grep "Używam bazy"
```

Jeśli widzisz: `💾 Używam bazy danych: SQLite`

**Rozwiązanie:**
1. Sprawdź czy DATABASE_URL jest w .env:
   ```bash
   cat ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram/.env | grep DATABASE_URL
   ```

2. Jeśli brak lub zakomentowane - dodaj/odkomentuj

3. Restart:
   ```bash
   sudo systemctl restart voice-notes-bot
   ```

### Dane nie pojawiają się w Supabase Dashboard

1. Sprawdź czy bot rzeczywiście używa Supabase (logi!)
2. Odśwież Supabase Dashboard (F5)
3. Sprawdź tabelę `notatki` i `zadania`
4. Sprawdź czy bot nie zgłasza błędów w logach

### Migracja się nie udała

```bash
# Sprawdź czy masz dane w SQLite
ls -lh ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram/voice_notes.db

# Sprawdź czy SQLite ma dane
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram
source venv/bin/activate
python view_database.py
deactivate

# Jeśli tak, spróbuj migracji ponownie
source venv/bin/activate
python migrate_to_supabase.py
deactivate
```

---

## 📚 Przydatne Linki

- **Supabase Dashboard:** https://supabase.com/dashboard
- **Supabase Docs:** https://supabase.com/docs
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/

---

## 🎯 Podsumowanie

**Masz teraz:**
- ✅ Bot działa na Linux Mint
- ✅ Baza danych w chmurze (Supabase)
- ✅ Automatyczne backupy
- ✅ Web Dashboard do przeglądania notatek
- ✅ Całkowicie darmowe
- ✅ Dane dostępne 24/7

**Ciesz się notatkamiz chmury!** ☁️📝

---

**Autor:** Voice Notes Bot System
**Data:** 2024-12-28
**Wersja:** 1.0 - Supabase Integration
