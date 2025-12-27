# 🌐 Setup Voice Notes Bot - 100% przez Przeglądarkę

Kompletny przewodnik instalacji Voice Notes Bota **bez instalowania niczego lokalnie** - wszystko przez Google Cloud Console w przeglądarce.

---

## 🎯 Co będziesz robić przez przeglądarkę

✅ **Tworzenie VM** - klikanie w Cloud Console
✅ **Edycja kodu** - Cloud Shell Editor (jak VS Code)
✅ **Konfiguracja bota** - terminal w przeglądarce
✅ **Zarządzanie** - SSH bezpośrednio z przeglądarki

**Zero instalacji lokalnych!** Wszystko działa w Chrome/Firefox/Safari.

---

## CZĘŚĆ 1: Przygotowanie (5 minut)

### Krok 1: Zaloguj się do Google Cloud Console

1. Otwórz przeglądarkę
2. Idź do: **https://console.cloud.google.com**
3. Zaloguj się kontem Google
4. Utwórz nowy projekt lub wybierz istniejący

### Krok 2: Włącz Cloud Shell

1. W prawym górnym rogu kliknij ikonę **>_** (Cloud Shell)
2. Poczekaj ~10 sekund na uruchomienie
3. Zobaczysz terminal Linux w dolnej części ekranu

**Gratulacje!** Masz teraz:
- ✅ Terminal Linux w przeglądarce
- ✅ Python 3.9+, git, gcloud preinstalowane
- ✅ 5 GB darmowego storage
- ✅ Edytor kodu (kliknij ikonę ołówka ✏️)

---

## CZĘŚĆ 2: Utwórz VM (f1-micro) - przez GUI

### Krok 1: Otwórz Compute Engine

1. W menu ☰ (lewy górny róg) → **Compute Engine** → **VM instances**
2. Jeśli pierwszy raz, kliknij **Enable** i poczekaj ~2 minuty

### Krok 2: Utwórz VM przez formularz

1. Kliknij **CREATE INSTANCE**
2. Wypełnij formularz:

**Podstawowe ustawienia:**
```
Name: voice-notes-bot
Region: us-west1 (Oregon)  ← WAŻNE: free tier!
Zone: us-west1-b
```

**Machine configuration:**
```
Series: N1
Machine type: f1-micro (1 vCPU, 614 MB memory)  ← WAŻNE: free tier!
```

**Boot disk:**
- Kliknij **CHANGE**
- Operating system: **Debian**
- Version: **Debian 11**
- Boot disk type: **Standard persistent disk**
- Size: **30 GB** (max free tier)
- Kliknij **SELECT**

**Firewall:**
- ☑ Allow HTTP traffic (opcjonalnie)
- ☑ Allow HTTPS traffic (opcjonalnie)

3. Kliknij **CREATE** (na dole)
4. Poczekaj ~1-2 minuty

✅ VM gotowe!

---

## CZĘŚĆ 3: Przygotuj Kod w Cloud Shell Editor

### Opcja A: Clone z GitHub (NAJLEPSZE jeśli masz repo)

W Cloud Shell (terminal w przeglądarce):

```bash
cd ~
git clone https://github.com/TWOJE_USERNAME/voice-notes-bot.git
cd voice-notes-bot
```

### Opcja B: Utwórz pliki ręcznie w Cloud Shell Editor

#### Krok 1: Otwórz Cloud Shell Editor

1. W Cloud Shell kliknij ikonę **✏️** (Open Editor)
2. Otworzy się edytor kodu (jak VS Code)

#### Krok 2: Utwórz strukturę projektu

W terminalu Cloud Shell:

```bash
mkdir -p ~/voice-notes-bot
cd ~/voice-notes-bot
```

#### Krok 3: Utwórz pliki przez edytor

W Cloud Shell Editor (lewy panel - File Explorer):

1. Kliknij prawym na `voice-notes-bot` folder → **New File**
2. Utwórz i edytuj każdy plik:

**Lista plików do utworzenia:**
- `bot.py`
- `config.py`
- `database.py`
- `ai_processor.py`
- `requirements-bot.txt`
- `.env.example`
- `backup_to_cloud.sh`
- `restore_from_cloud.sh`

**Skopiuj zawartość z lokalnych plików** (lub z GitHub) i wklej do każdego pliku w edytorze.

💡 **Tip:** Możesz otworzyć dwa okna przeglądarki obok siebie:
- Lewe: Twoje lokalne pliki / GitHub
- Prawe: Cloud Shell Editor
- Copy-paste między nimi!

---

## CZĘŚĆ 4: Upload Plików na VM (przez Cloud Shell)

### Metoda: gcloud compute scp (z Cloud Shell)

W Cloud Shell terminal:

```bash
# Sprawdź czy pliki są gotowe
ls -la ~/voice-notes-bot/

# Upload wszystkich plików na VM
gcloud compute scp --recurse ~/voice-notes-bot/* voice-notes-bot:~/voice-notes-bot/
```

**Alternatywnie:** Możesz SSH do VM i utworzyć pliki bezpośrednio tam (patrz następna sekcja).

---

## CZĘŚĆ 5: SSH do VM i Instalacja (przez przeglądarkę)

### Krok 1: Połącz się z VM przez przeglądarkę

1. W Google Cloud Console → **Compute Engine** → **VM instances**
2. Znajdź `voice-notes-bot`
3. W kolumnie **Connect** kliknij **SSH**
4. Otworzy się nowe okno z terminalem SSH ✅

### Krok 2: Aktualizacja systemu

W terminalu SSH (w przeglądarce):

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git
```

### Krok 3: Sprawdź czy pliki są na VM

```bash
ls -la ~/voice-notes-bot/
```

**Jeśli brak plików**, utwórz je bezpośrednio w SSH:

```bash
mkdir -p ~/voice-notes-bot
cd ~/voice-notes-bot

# Użyj nano do utworzenia każdego pliku
nano bot.py
# Wklej zawartość (Ctrl+Shift+V), zapisz (Ctrl+X → Y → Enter)

nano config.py
# ... itd
```

### Krok 4: Instalacja zależności

```bash
cd ~/voice-notes-bot

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Instalacja
pip install --upgrade pip
pip install -r requirements-bot.txt
```

### Krok 5: Konfiguracja .env

```bash
nano .env
```

Wklej (zastąp swoimi danymi):

```env
TELEGRAM_BOT_TOKEN=twoj_token_z_botfather
ALLOWED_USER_IDS=twoj_telegram_user_id
OPENAI_API_KEY=twoj_openai_api_key
DATABASE_PATH=voice_notes.db
```

Zapisz: **Ctrl+X** → **Y** → **Enter**

### Krok 6: Test bota

```bash
python bot.py
```

Powinieneś zobaczyć:
```
🚀 Bot uruchomiony!
```

Testuj w Telegram! Jeśli działa, przerwij: **Ctrl+C**

---

## CZĘŚĆ 6: Uruchomienie 24/7 (systemd)

W terminalu SSH (w przeglądarce):

### Krok 1: Sprawdź swoją nazwę użytkownika

```bash
whoami
```

Zapamiętaj output (np. `jan_kowalski_gmail_com`)

### Krok 2: Utwórz systemd service

```bash
sudo nano /etc/systemd/system/voice-notes-bot.service
```

Wklej (ZASTĄP `YOUR_USERNAME` outputem z `whoami`):

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

**Przykład** (jeśli `whoami` → `jan_kowalski_gmail_com`):

```ini
[Unit]
Description=Voice Notes Telegram Bot
After=network.target

[Service]
Type=simple
User=jan_kowalski_gmail_com
WorkingDirectory=/home/jan_kowalski_gmail_com/voice-notes-bot
Environment="PATH=/home/jan_kowalski_gmail_com/voice-notes-bot/venv/bin"
ExecStart=/home/jan_kowalski_gmail_com/voice-notes-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Zapisz: **Ctrl+X** → **Y** → **Enter**

### Krok 3: Uruchom service

```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-notes-bot
sudo systemctl start voice-notes-bot
```

### Krok 4: Sprawdź status

```bash
sudo systemctl status voice-notes-bot
```

Powinieneś zobaczyć:
```
● voice-notes-bot.service - Voice Notes Telegram Bot
   Active: active (running)
```

**Logi na żywo:**
```bash
sudo journalctl -u voice-notes-bot -f
```

(Wyjdź: **Ctrl+C**)

---

## CZĘŚĆ 7: Setup Backupów do Cloud Storage (przez przeglądarkę)

### Krok 1: Konfiguracja Cloud Storage (w Cloud Shell)

Przejdź z powrotem do **Cloud Shell** (nie SSH do VM):

1. Kliknij **>_** w prawym górnym rogu
2. W Cloud Shell terminal:

```bash
# Zaloguj się (jeśli trzeba)
gcloud auth login

# Ustaw projekt
gcloud config set project YOUR_PROJECT_ID

# Utwórz bucket (nazwa musi być globalnie unikalna)
BUCKET_NAME="voice-notes-backups-$(whoami)-$(date +%s)"
gsutil mb -l europe-central2 gs://${BUCKET_NAME}

# Lifecycle policy (auto-delete po 30 dniach)
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle.json gs://${BUCKET_NAME}

# Pokaż nazwę bucket (ZAPISZ!)
echo "✅ Bucket utworzony: gs://${BUCKET_NAME}"
```

### Krok 2: Konfiguracja backupu na VM

Przejdź do **SSH VM** (kliknij SSH przy VM w Console):

```bash
cd ~/voice-notes-bot

# Edytuj skrypt backupu
nano backup_to_cloud.sh
```

**Znajdź linię:**
```bash
GCS_BUCKET="gs://voice-notes-backups-$(whoami)"
```

**Zmień na** (wklej nazwę bucket z poprzedniego kroku):
```bash
GCS_BUCKET="gs://voice-notes-backups-YOUR-UNIQUE-NAME"
```

Zapisz: **Ctrl+X** → **Y** → **Enter**

### Krok 3: Nadaj uprawnienia i testuj

```bash
chmod +x backup_to_cloud.sh restore_from_cloud.sh

# Zaloguj gcloud na VM
gcloud auth login
# Otwórz link w przeglądarce, zaloguj się, skopiuj kod, wklej do terminala

# Test backupu
./backup_to_cloud.sh
```

Powinieneś zobaczyć:
```
✅ Backup zakończony pomyślnie!
```

### Krok 4: Automatyzacja (cron)

```bash
crontab -e
```

Wybierz edytor (np. `1` dla nano)

Dodaj na końcu:
```
0 */6 * * * /home/YOUR_USERNAME/voice-notes-bot/backup_to_cloud.sh >> /home/YOUR_USERNAME/voice-notes-bot/backup.log 2>&1
```

(Zastąp `YOUR_USERNAME` swoją nazwą z `whoami`)

Zapisz: **Ctrl+X** → **Y** → **Enter**

✅ Backupy będą się wykonywać co 6h automatycznie!

---

## 🎯 Weryfikacja - Wszystko Działa?

### Checklist:

W Cloud Console (przeglądarka):

- [ ] VM `voice-notes-bot` jest **Running** (zielona ikona)
- [ ] Możesz kliknąć **SSH** i połączyć się
- [ ] W SSH: `sudo systemctl status voice-notes-bot` pokazuje **active (running)**
- [ ] W Telegram: Bot odpowiada na `/start`
- [ ] W Telegram: Możesz wysłać voice message i otrzymasz notatkę
- [ ] Cloud Storage bucket istnieje: sprawdź w Console → **Cloud Storage** → **Buckets**
- [ ] Backup działa: w SSH `ls -la backups/` pokazuje pliki `.db.gz`

### Sprawdź logi (w SSH):

```bash
# Logi bota
sudo journalctl -u voice-notes-bot -n 50

# Logi backupów
tail -f ~/voice-notes-bot/backup.log
```

---

## 🛠️ Zarządzanie przez Przeglądarkę

### Restart bota

1. **Compute Engine** → **VM instances** → `voice-notes-bot`
2. Kliknij **SSH**
3. W terminalu:
```bash
sudo systemctl restart voice-notes-bot
```

### Aktualizacja kodu

**Jeśli masz GitHub:**
```bash
cd ~/voice-notes-bot
git pull
sudo systemctl restart voice-notes-bot
```

**Jeśli edytujesz ręcznie:**
1. SSH do VM
2. `nano bot.py` (lub inny plik)
3. Edytuj, zapisz
4. `sudo systemctl restart voice-notes-bot`

### Sprawdź backupy w Cloud Storage

1. W Cloud Console → **Cloud Storage** → **Buckets**
2. Kliknij na swój bucket
3. Zobacz listę backupów
4. Możesz pobrać dowolny backup (kliknij → Download)

### View bazy danych

W SSH do VM:

```bash
cd ~/voice-notes-bot
source venv/bin/activate
python view_database.py
```

---

## 💡 Dodatkowe Narzędzia Webowe

### Cloud Shell Editor (edytor kodu)

1. W Cloud Shell kliknij **✏️** (Open Editor)
2. Edytuj pliki jak w VS Code
3. Terminal + edytor w jednym oknie!

### Cloud Monitoring (opcjonalnie)

1. **Monitoring** → **Dashboards**
2. Zobacz CPU, RAM, disk usage VM
3. Ustaw alerty (np. gdy RAM > 90%)

### Cloud Logging (opcjonalnie)

1. **Logging** → **Logs Explorer**
2. Filtruj logi z VM
3. Szukaj błędów, debuguj

---

## 🔒 Bezpieczeństwo

### Firewall (opcjonalnie)

W SSH do VM:

```bash
sudo apt install -y ufw
sudo ufw allow ssh
sudo ufw enable
```

### Automatyczne aktualizacje

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Wybierz: **Yes**

---

## 💰 Koszty - FREE TIER

| Zasób | Limit Free | Twoje Użycie | Koszt |
|-------|-----------|--------------|-------|
| f1-micro VM | 1 instance | 1 instance | **$0** |
| Storage 30GB | 30 GB | 30 GB | **$0** |
| Cloud Storage | 5 GB | ~0.5 GB | **$0** |
| Cloud Shell | 50h/tydzień | ~1h setup | **$0** |
| **TOTAL** | | | **$0/mies** ✅ |

---

## 🐛 Troubleshooting

### Cloud Shell timeout

Cloud Shell wyłącza się po 20 min bezczynności. To OK!
- Kliknij **>_** ponownie
- Wszystkie pliki w `~/voice-notes-bot` są zachowane (5GB persistent storage)

### SSH nie działa

1. Sprawdź czy VM jest **Running** (zielona ikona)
2. Spróbuj **RESET** VM: VM instances → ⋮ (menu) → Reset
3. Poczekaj 1 minutę i spróbuj SSH ponownie

### Bot nie odpowiada

```bash
# SSH do VM, sprawdź logi
sudo journalctl -u voice-notes-bot -n 100

# Restart
sudo systemctl restart voice-notes-bot
```

### Out of memory (f1-micro ma tylko 614MB)

```bash
# Dodaj swap
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Restart bota
sudo systemctl restart voice-notes-bot
```

---

## ✅ Gotowe!

Wszystko zrobione **100% przez przeglądarkę**! 🎉

**Co masz teraz:**
- ✅ Bot działa 24/7 na Google Cloud (darmowo)
- ✅ Automatyczne backupy co 6h do Cloud Storage
- ✅ Zarządzanie przez przeglądarkę (Cloud Console + SSH)
- ✅ Edytor kodu w przeglądarce (Cloud Shell Editor)
- ✅ Zero instalacji lokalnych!

**Następne kroki:**
1. Wyślij voice message do bota w Telegram
2. Sprawdź czy działa
3. Ciesz się automatycznymi notatkami! 🎙️

---

## 📚 Przydatne Linki

- **Google Cloud Console:** https://console.cloud.google.com
- **Cloud Shell Tutorial:** https://cloud.google.com/shell/docs/launching-cloud-shell
- **Compute Engine Docs:** https://cloud.google.com/compute/docs
- **Cloud Storage Browser:** https://console.cloud.google.com/storage/browser

**Wszystko w przeglądarce, zero instalacji! 🚀**

---

**Autor:** Voice Notes Bot System
**Data:** 2024-01-15
**Wersja:** 1.0 - Web-Only Setup
