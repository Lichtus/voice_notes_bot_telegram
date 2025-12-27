# 💻 Setup Voice Notes Bot na Linux Mint

Prosty przewodnik instalacji bota bezpośrednio na Twoim laptopie z Linux Mint.

**Czas instalacji: 10 minut**

---

## 🎯 Co otrzymasz

- ✅ Bot działa **lokalnie** na Twoim laptopie
- ✅ Auto-start po restarcie systemu
- ✅ Niskie zużycie zasobów (~50 MB RAM)
- ✅ Wszystko pod Twoją kontrolą
- ✅ Opcjonalne backupy do Cloud Storage (darmowe)

## ⚠️ Wymagania

- ✅ Laptop z Linux Mint (lub Ubuntu/Debian)
- ✅ Połączenie z internetem
- ✅ Laptop musi działać gdy chcesz używać bota
- ✅ Telegram Bot Token (z @BotFather)
- ✅ OpenAI API Key
- ✅ Twój Telegram User ID

---

## CZĘŚĆ 1: Przygotowanie Tokenów (5 minut)

Zanim zaczniesz, przygotuj w notatniku:

### 1. Telegram Bot Token

1. Otwórz Telegram
2. Znajdź **@BotFather**
3. Wyślij `/mybots`
4. Wybierz swojego bota → **API Token**
5. Skopiuj token (wygląda jak: `7123456789:AAHdqT...`)

### 2. Telegram User ID

1. W Telegram znajdź **@userinfobot**
2. Wyślij `/start`
3. Skopiuj swoje **ID** (liczba np. `123456789`)

### 3. OpenAI API Key

1. Otwórz: https://platform.openai.com/api-keys
2. Zaloguj się
3. Kliknij **Create new secret key**
4. Skopiuj klucz (wygląda jak: `sk-proj-...`)

**Zapisz te 3 wartości w notatniku** - zaraz będą potrzebne!

---

## CZĘŚĆ 2: Instalacja na Linux Mint (10 minut)

### Krok 1: Otwórz Terminal

Naciśnij: **Ctrl+Alt+T**

### Krok 2: Instalacja zależności systemowych

W terminalu wklej:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git
```

Wpisz hasło jeśli poprosi.
⏰ Czekaj ~1-2 minuty

### Krok 3: Przejdź do folderu z kodem

**Jeśli masz już kod lokalnie** (w `/home/user/25_wrozenia_aplikacji_notatki`):

```bash
cd ~/25_wrozenia_aplikacji_notatki
```

**Jeśli masz kod na GitHub**:

```bash
cd ~
git clone -b claude/voice-notes-app-design-9rEYp https://github.com/TWOJE_USERNAME/voice-notes-bot.git
cd voice-notes-bot
```

**Sprawdź czy pliki są:**

```bash
ls -la
```

Powinieneś zobaczyć: `bot.py`, `config.py`, `database.py`, `ai_processor.py`, etc.

### Krok 4: Utwórz Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

Powinieneś zobaczyć `(venv)` przed promptem w terminalu.

### Krok 5: Instalacja zależności Python

```bash
pip install --upgrade pip
pip install -r requirements-bot.txt
```

⏰ Czekaj ~2-3 minuty

### Krok 6: Konfiguracja - Utwórz plik .env

**Sprawdź czy masz plik .env:**

```bash
ls -la .env
```

**Jeśli NIE MA pliku .env**, utwórz go:

```bash
nano .env
```

**Jeśli JEST plik .env**, edytuj go:

```bash
nano .env
```

**Wklej lub edytuj** (zastąp wartościami z notatnika):

```env
TELEGRAM_BOT_TOKEN=twoj_token_z_botfather
ALLOWED_USER_IDS=twoj_telegram_user_id
OPENAI_API_KEY=twoj_openai_api_key
DATABASE_PATH=voice_notes.db
```

**Przykład** (z prawdziwymi danymi):

```env
TELEGRAM_BOT_TOKEN=7123456789:AAHdqTnQx_abcdefghijklmnopqrstuv
ALLOWED_USER_IDS=123456789
OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890
DATABASE_PATH=voice_notes.db
```

**Zapisz plik:**
- Naciśnij **Ctrl+X**
- Naciśnij **Y**
- Naciśnij **Enter**

### Krok 7: TEST - Uruchom bota ręcznie

```bash
python bot.py
```

Powinieneś zobaczyć:
```
🚀 Bot uruchomiony!
```

**Testuj w Telegram:**
1. Otwórz Telegram na telefonie
2. Znajdź swojego bota
3. Wyślij `/start`
4. Nagraj i wyślij **voice message**

**Działa?** 🎉 Świetnie!

**W terminalu naciśnij Ctrl+C** aby zatrzymać bota.

---

## CZĘŚĆ 3: Auto-Start - Bot działa w tle (5 minut)

Teraz sprawimy, że bot będzie:
- ✅ Działał w tle (nie trzeba terminala)
- ✅ Automatycznie startował po restarcie laptopa
- ✅ Automatycznie restartował się w razie błędu

### Krok 1: Sprawdź swoją nazwę użytkownika

```bash
whoami
```

Zapamiętaj output (np. `jan` lub `user`)

### Krok 2: Sprawdź pełną ścieżkę do folderu bota

```bash
pwd
```

Zapamiętaj output (np. `/home/user/25_wrozenia_aplikacji_notatki`)

### Krok 3: Utwórz systemd service

```bash
sudo nano /etc/systemd/system/voice-notes-bot.service
```

**Wklej poniższy kod** i **ZASTĄP**:
- `YOUR_USERNAME` → wynik z `whoami`
- `/home/YOUR_USERNAME/voice-notes-bot` → wynik z `pwd`

```ini
[Unit]
Description=Voice Notes Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/voice-notes-bot
Environment="PATH=/home/YOUR_USERNAME/voice-notes-bot/venv/bin"
ExecStart=/home/YOUR_USERNAME/voice-notes-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**PRZYKŁAD** (jeśli `whoami` → `user` i `pwd` → `/home/user/25_wrozenia_aplikacji_notatki`):

```ini
[Unit]
Description=Voice Notes Telegram Bot
After=network.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/25_wrozenia_aplikacji_notatki
Environment="PATH=/home/user/25_wrozenia_aplikacji_notatki/venv/bin"
ExecStart=/home/user/25_wrozenia_aplikacji_notatki/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Zapisz:**
- **Ctrl+X**
- **Y**
- **Enter**

### Krok 4: Uruchom service

```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-notes-bot
sudo systemctl start voice-notes-bot
```

### Krok 5: Sprawdź status

```bash
sudo systemctl status voice-notes-bot
```

Powinieneś zobaczyć:
```
● voice-notes-bot.service - Voice Notes Telegram Bot
   Loaded: loaded (/etc/systemd/system/voice-notes-bot.service; enabled)
   Active: active (running) since ...  ✅
```

Naciśnij **Q** aby wyjść.

---

## ✅ GOTOWE! Bot działa w tle!

**Możesz zamknąć terminal** - bot będzie działał dalej!

**Testuj w Telegram:**
- Wyślij voice message
- Sprawdź czy działa
- Przetestuj wyszukiwanie: "szukaj test"
- Sprawdź zadania: `/zadania`

---

## 🛠️ Zarządzanie Botem

### Zatrzymaj bota

```bash
sudo systemctl stop voice-notes-bot
```

### Uruchom bota

```bash
sudo systemctl start voice-notes-bot
```

### Restart bota

```bash
sudo systemctl restart voice-notes-bot
```

### Sprawdź status

```bash
sudo systemctl status voice-notes-bot
```

### Zobacz logi (ostatnie 50 linii)

```bash
sudo journalctl -u voice-notes-bot -n 50
```

### Logi na żywo (real-time)

```bash
sudo journalctl -u voice-notes-bot -f
```

(Wyjdź: **Ctrl+C**)

---

## 🔄 Aktualizacja Kodu

Jeśli edytujesz pliki (np. `bot.py`):

```bash
# 1. Edytuj pliki
nano ~/25_wrozenia_aplikacji_notatki/bot.py

# 2. Restart bota
sudo systemctl restart voice-notes-bot

# 3. Sprawdź logi
sudo journalctl -u voice-notes-bot -n 20
```

Jeśli masz kod na GitHub i chcesz pobrać nowe zmiany:

```bash
cd ~/25_wrozenia_aplikacji_notatki
git pull
sudo systemctl restart voice-notes-bot
```

---

## 📊 Zobacz Bazę Danych

```bash
cd ~/25_wrozenia_aplikacji_notatki
source venv/bin/activate
python view_database.py
```

---

## 💾 Backupy (OPCJONALNE)

### Opcja A: Prosty lokalny backup

**Ręczny backup:**

```bash
cp ~/25_wrozenia_aplikacji_notatki/voice_notes.db ~/voice_notes_backup_$(date +%Y%m%d).db
```

**Automatyczny backup codziennie o 3:00:**

```bash
crontab -e
```

Wybierz edytor (np. `1` dla nano), dodaj na końcu:

```
0 3 * * * cp ~/25_wrozenia_aplikacji_notatki/voice_notes.db ~/backups/voice_notes_$(date +\%Y\%m\%d).db
```

Utwórz folder backupów:
```bash
mkdir -p ~/backups
```

### Opcja B: Backupy do Google Cloud Storage (DARMOWE)

**Pełna instrukcja:** Zobacz `CLOUD_STORAGE_SETUP.md`

**Quick setup:**

1. Zainstaluj gcloud SDK:
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

2. Ustaw bucket w skrypcie:
```bash
nano ~/25_wrozenia_aplikacji_notatki/backup_to_cloud.sh
# Zmień: GCS_BUCKET="gs://voice-notes-backups-twoja-nazwa"
```

3. Test backupu:
```bash
cd ~/25_wrozenia_aplikacji_notatki
./backup_to_cloud.sh
```

4. Automatyzacja (co 6h):
```bash
crontab -e
# Dodaj: 0 */6 * * * /home/user/25_wrozenia_aplikacji_notatki/backup_to_cloud.sh >> /home/user/25_wrozenia_aplikacji_notatki/backup.log 2>&1
```

✅ Backupy będą się tworzyć co 6h automatycznie do Cloud Storage (darmowe w free tier)!

---

## 🔋 Zużycie Zasobów

Bot jest bardzo lekki:

- **RAM:** ~50 MB
- **CPU:** <1% (idle), ~5-10% (podczas przetwarzania voice)
- **Dysk:** ~200 MB (kod + dependencies)
- **Baza danych:** ~1-5 MB (w zależności od liczby notatek)

### Zużycie Prądu (laptop)

Typowy laptop:
- **Idle:** ~10-20W
- **24/7 przez miesiąc:** ~11 kWh
- **Koszt:** ~9-10 zł/miesiąc (przy 0.80 zł/kWh)

**Tips oszczędzania energii:**
- Ustaw jasność ekranu na minimum (jeśli laptop leży zamknięty)
- Wyłącz WiFi jeśli używasz ethernet
- W ustawieniach zasilania: "Nie usypiaj nigdy" (gdy podłączony do prądu)

---

## 🔒 Bezpieczeństwo

### 1. Firewall (opcjonalnie)

Bot **NIE wymaga** otwartych portów - komunikuje się outbound z Telegram API.

Jeśli chcesz dodatkowo zabezpieczyć laptop:

```bash
sudo ufw enable
sudo ufw status
```

### 2. Uprawnienia do pliku .env

Upewnij się że tylko Ty możesz czytać .env (zawiera tokeny):

```bash
chmod 600 ~/25_wrozenia_aplikacji_notatki/.env
```

### 3. Automatyczne aktualizacje bezpieczeństwa

Linux Mint ma to domyślnie włączone, ale możesz sprawdzić:

**Menu → Administration → Update Manager → Edit → Preferences → Automation**

---

## 🌙 Bot podczas uśpienia/hibernacji laptopa

### ⚠️ WAŻNE:

Jeśli laptop:
- **Usypia się** (suspend) → bot przestaje działać
- **Hibernuje** → bot przestaje działać
- **Zamykasz klapę** → zależy od ustawień

### Rozwiązanie: Wyłącz uśpienie dla laptopa podłączonego do prądu

**Menu → System Settings → Power Management**

Ustaw:
- **When the lid is closed:** Do nothing
- **Put computer to sleep when inactive for:** Never (gdy podłączony do AC)

Lub w terminalu:

```bash
# Sprawdź obecne ustawienia
gsettings get org.cinnamon.settings-daemon.plugins.power sleep-inactive-ac-timeout

# Ustaw "nigdy nie usypiaj" gdy podłączony do prądu (0 = never)
gsettings set org.cinnamon.settings-daemon.plugins.power sleep-inactive-ac-timeout 0
```

---

## 🐛 Troubleshooting

### Bot nie odpowiada w Telegram

**1. Sprawdź czy service działa:**
```bash
sudo systemctl status voice-notes-bot
```

Jeśli `inactive` lub `failed`:
```bash
sudo systemctl start voice-notes-bot
```

**2. Sprawdź logi:**
```bash
sudo journalctl -u voice-notes-bot -n 50
```

Szukaj błędów (na czerwono).

**3. Sprawdź połączenie z internetem:**
```bash
ping -c 3 google.com
```

### Błąd: "ModuleNotFoundError"

Virtual environment nie jest aktywowany. Sprawdź ścieżkę w service:

```bash
sudo nano /etc/systemd/system/voice-notes-bot.service
```

Upewnij się że ścieżka do `ExecStart` jest poprawna.

### Błąd: "Can't connect to OpenAI API"

Sprawdź czy klucz API jest poprawny:

```bash
cat ~/25_wrozenia_aplikacji_notatki/.env | grep OPENAI
```

### Błąd: "Telegram Conflict: terminated by other getUpdates"

Masz dwa boty uruchomione jednocześnie. Zabij wszystkie:

```bash
sudo systemctl stop voice-notes-bot
killall python
killall python3
sudo systemctl start voice-notes-bot
```

### Po restarcie laptopa bot nie startuje

Sprawdź czy service jest enabled:

```bash
sudo systemctl is-enabled voice-notes-bot
```

Jeśli `disabled`:
```bash
sudo systemctl enable voice-notes-bot
```

---

## 📊 Monitoring

### Sprawdź zużycie zasobów

```bash
# Procesory i RAM
htop

# (Instalacja jeśli nie masz: sudo apt install htop)
# Szukaj procesu "python bot.py"
# Wyjście: Q
```

### Rozmiar bazy danych

```bash
du -h ~/25_wrozenia_aplikacji_notatki/voice_notes.db
```

### Ile notatek w bazie?

```bash
cd ~/25_wrozenia_aplikacji_notatki
source venv/bin/activate
python view_database.py
```

### Uptime bota

```bash
sudo systemctl status voice-notes-bot | grep Active
```

---

## 💡 Dodatkowe Wskazówki

### Dostęp do bota z innego komputera/telefonu

Bot **już działa** z telefonu przez Telegram! Nie musisz nic konfigurować.

Telegram Bot API działa tak:
1. Wysyłasz voice message z telefonu → Telegram
2. Telegram → Bot na Twoim laptopie (outbound connection)
3. Bot przetwarza → odpowiedź wraca do Ciebie

**Nie potrzebujesz:**
- Publicznego IP
- Otwartych portów
- Konfiguracji routera

### Używanie bota gdy laptop jest w innym pokoju

Idealnie! Bot działa w tle 24/7. Możesz:
- Zamknąć ekran (laptop leży zamknięty)
- Odłączyć monitor
- Używać bota z telefonu z dowolnego miejsca na świecie

### Co gdy wyjeżdżam i laptop zostaje w domu?

**Opcja 1:** Zostaw laptop włączony
- Bot będzie działał normalnie
- Możesz używać z telefonu z dowolnego miejsca
- Pamiętaj o zasilaniu i wyłączeniu uśpienia

**Opcja 2:** Przenieś bota na Google Cloud
- Wtedy bot działa zawsze, niezależnie od laptopa
- Instrukcja: `GOOGLE_CLOUD_WEB_SETUP.md`

---

## ✅ Checklist - Wszystko Działa?

Sprawdź po kolei:

- [ ] Service jest aktywny: `sudo systemctl status voice-notes-bot` → **active (running)**
- [ ] Bot odpowiada na `/start` w Telegram
- [ ] Możesz wysłać voice message i otrzymasz notatkę
- [ ] Wyszukiwanie działa: "szukaj test"
- [ ] Zadania działają: `/zadania`
- [ ] Service startuje po restarcie: `sudo systemctl is-enabled voice-notes-bot` → **enabled**
- [ ] Laptop nie usypia się gdy podłączony do prądu
- [ ] (Opcjonalnie) Backupy działają

**Wszystko ✅?** Gratulacje! Bot działa! 🎉

---

## 🎯 Co Dalej?

### Podstawowe użycie:
- Nagrywaj voice messages → automatyczne notatki
- Szukaj: "szukaj słowo kluczowe"
- Zarządzaj zadaniami: `/zadania`, `/zakoncz_zadanie 1`

### Zaawansowane:
- Setup backupów do Cloud Storage (patrz wyżej)
- Dodaj więcej użytkowników: edytuj `ALLOWED_USER_IDS` w `.env`
- Customizuj prompty: edytuj `ai_processor.py`

### Przeniesienie na Google Cloud (opcjonalnie):
- Jeśli chcesz aby bot działał zawsze (niezależnie od laptopa)
- Instrukcja: `GOOGLE_CLOUD_WEB_SETUP.md`

---

## 🆘 Potrzebujesz Pomocy?

**Logi są Twoim przyjacielem:**

```bash
sudo journalctl -u voice-notes-bot -f
```

Uruchom to w jednym terminalu, a w Telegramie wyślij coś do bota.
Zobaczysz na żywo co się dzieje!

**Jeśli coś nie działa:**
1. Sprawdź logi
2. Sprawdź status service
3. Sprawdź połączenie z internetem
4. Sprawdź `.env` (czy tokeny są poprawne)

---

## 📚 Dokumentacja

- **`README.md`** - Ogólna dokumentacja projektu
- **`CLOUD_STORAGE_SETUP.md`** - Setup backupów do Cloud Storage
- **`GOOGLE_CLOUD_WEB_SETUP.md`** - Alternatywa: deployment na Google Cloud

---

**Autor:** Voice Notes Bot System
**Data:** 2024-01-15
**Wersja:** 1.0 - Linux Mint Setup
**Platforma:** Linux Mint / Ubuntu / Debian

---

## 🎉 Gotowe!

Twój bot działa teraz lokalnie na Linux Mint!

**Ciesz się automatycznymi notatkami!** 🎙️📝
