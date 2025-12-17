# ☁️ Deployment na Google Cloud (f1-micro - DARMOWY)

Ten przewodnik krok po kroku pomoże Ci wdrożyć Voice Notes Bota na Google Cloud Compute Engine używając **darmowego f1-micro instance**.

## 🎯 Co otrzymasz

- ✅ **Zawsze darmowy** f1-micro VM (w ramach Google Cloud Free Tier)
- ✅ Bot działa **24/7 non-stop**
- ✅ 30 GB storage
- ✅ Zewnętrzny IP (statyczny opcjonalnie)
- ✅ Automatyczny restart bota

## 📋 Wymagania

1. Konto Google (Gmail)
2. Karta kredytowa/debetowa (do weryfikacji, **nie pobiorą pieniędzy** na free tier)
3. Telegram Bot Token (z @BotFather)
4. OpenAI API Key
5. Twój Telegram User ID

---

## CZĘŚĆ 1: Założenie konta Google Cloud

### Krok 1: Rejestracja w Google Cloud

1. Przejdź do: https://cloud.google.com/free
2. Kliknij **"Get started for free"** lub **"Wypróbuj bezpłatnie"**
3. Zaloguj się kontem Google
4. Uzupełnij dane:
   - Kraj
   - Typ konta: Individual (Osobiste)
   - Adres
   - **Dane karty** (tylko weryfikacja, nie pobiorą pieniędzy)
5. Akceptuj regulamin
6. Kliknij **"Start my free trial"**

**Otrzymujesz:**
- $300 kredytu na 90 dni (do testowania)
- **Zawsze darmowy f1-micro** (nawet po 90 dniach!)

---

## CZĘŚĆ 2: Tworzenie VM Instance (f1-micro)

### Krok 1: Otwórz Google Cloud Console

1. Przejdź do: https://console.cloud.google.com
2. W menu hamburger (☰) → **Compute Engine** → **VM instances**
3. Jeśli to pierwszy raz, poczekaj na inicjalizację Compute Engine (~2 min)

### Krok 2: Utwórz nowy VM

1. Kliknij **"CREATE INSTANCE"** (Utwórz instancję)

2. **Konfiguracja podstawowa:**
   - **Name:** `voice-notes-bot` (lub inna nazwa)
   - **Region:** Wybierz jeden z darmowych regionów:
     - `us-west1` (Oregon)
     - `us-central1` (Iowa)
     - `us-east1` (South Carolina)
   - **Zone:** dowolna (np. `us-west1-b`)

3. **Machine configuration:**
   - **Series:** N1
   - **Machine type:** Kliknij **"E2-micro"** i wybierz z listy **"f1-micro (1 vCPU, 614 MB memory)"**

   ⚠️ **WAŻNE:** Upewnij się że to **f1-micro**, nie e2-micro! f1-micro jest zawsze darmowy.

4. **Boot disk:**
   - Kliknij **"CHANGE"**
   - **Operating system:** Debian
   - **Version:** Debian 11 (lub nowszy)
   - **Boot disk type:** Standard persistent disk
   - **Size:** 30 GB (max darmowy)
   - Kliknij **"SELECT"**

5. **Firewall:**
   - ✅ Zaznacz: **Allow HTTP traffic** (opcjonalne)
   - ✅ Zaznacz: **Allow HTTPS traffic** (opcjonalne)

6. Kliknij **"CREATE"** (na dole strony)

**Czas tworzenia:** ~1-2 minuty

---

## CZĘŚĆ 3: Połączenie z VM przez SSH

### Krok 1: Połącz się z VM

1. W liście VM instances znajdź swoją maszynę `voice-notes-bot`
2. W kolumnie **"Connect"** kliknij **"SSH"**
3. Otworzy się nowe okno z terminalem

**Alternatywnie:** Możesz użyć `gcloud` CLI lub standardowego SSH.

### Krok 2: Aktualizacja systemu

W terminalu SSH wpisz:

```bash
sudo apt update
sudo apt upgrade -y
```

---

## CZĘŚĆ 4: Instalacja Pythona i zależności

### Krok 1: Sprawdź wersję Pythona

```bash
python3 --version
```

Powinieneś zobaczyć Python 3.9+ (Debian 11 ma 3.9 domyślnie).

### Krok 2: Zainstaluj pip i venv

```bash
sudo apt install -y python3-pip python3-venv git
```

### Krok 3: Utwórz katalog dla bota

```bash
mkdir -p ~/voice-notes-bot
cd ~/voice-notes-bot
```

---

## CZĘŚĆ 5: Upload kodu bota na VM

Masz 3 opcje:

### **OPCJA A: Git clone (NAJLEPSZA)**

Jeśli masz kod w repozytorium Git:

```bash
cd ~
git clone <twój-repo-url> voice-notes-bot
cd voice-notes-bot
```

### **OPCJA B: Upload przez SCP**

Z lokalnego komputera (nie w SSH):

```bash
gcloud compute scp --recurse ./25_wrozenia_aplikacji_notatki/* voice-notes-bot:~/voice-notes-bot/
```

### **OPCJA C: Ręczne kopiowanie plików**

1. W terminalu SSH stwórz pliki:

```bash
cd ~/voice-notes-bot
nano bot.py
```

2. Skopiuj zawartość `bot.py` i wklej (Ctrl+Shift+V)
3. Zapisz: Ctrl+X → Y → Enter
4. Powtórz dla: `config.py`, `database.py`, `ai_processor.py`, `requirements-bot.txt`

---

## CZĘŚĆ 6: Instalacja zależności Python

### Krok 1: Utwórz virtual environment

```bash
cd ~/voice-notes-bot
python3 -m venv venv
source venv/bin/activate
```

Powinieneś zobaczyć `(venv)` przed promptem.

### Krok 2: Zainstaluj requirements

```bash
pip install --upgrade pip
pip install -r requirements-bot.txt
```

**Czas instalacji:** ~2-3 minuty (f1-micro ma mało RAM, więc może być wolno).

---

## CZĘŚĆ 7: Konfiguracja bota (.env)

### Krok 1: Utwórz plik .env

```bash
nano .env
```

### Krok 2: Wklej konfigurację

```env
TELEGRAM_BOT_TOKEN=twoj_bot_token_z_botfather
ALLOWED_USER_IDS=twoj_telegram_user_id
OPENAI_API_KEY=twoj_openai_api_key
DATABASE_PATH=voice_notes.db
```

**Zastąp:**
- `twoj_bot_token_z_botfather` - token z @BotFather
- `twoj_telegram_user_id` - Twój ID z @userinfobot
- `twoj_openai_api_key` - klucz z https://platform.openai.com/api-keys

### Krok 3: Zapisz

Ctrl+X → Y → Enter

---

## CZĘŚĆ 8: Testowanie bota

### Krok 1: Uruchom bota ręcznie (test)

```bash
cd ~/voice-notes-bot
source venv/bin/activate
python bot.py
```

Powinieneś zobaczyć:
```
🚀 Bot uruchomiony!
```

### Krok 2: Testuj w Telegram

1. Otwórz Telegram
2. Znajdź swojego bota
3. Wyślij `/start`
4. Wyślij voice message

Jeśli działa - świetnie! Przerwij bota: Ctrl+C

---

## CZĘŚĆ 9: Uruchomienie bota w tle (systemd)

Aby bot działał 24/7 i automatycznie restartował, użyjemy **systemd**.

### Krok 1: Utwórz plik service

```bash
sudo nano /etc/systemd/system/voice-notes-bot.service
```

### Krok 2: Wklej konfigurację

**WAŻNE:** Zamień `YOUR_USERNAME` na swoją nazwę użytkownika (sprawdź przez `whoami`).

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

**Przykład** (jeśli username to `john`):

```ini
[Unit]
Description=Voice Notes Telegram Bot
After=network.target

[Service]
Type=simple
User=john
WorkingDirectory=/home/john/voice-notes-bot
Environment="PATH=/home/john/voice-notes-bot/venv/bin"
ExecStart=/home/john/voice-notes-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Krok 3: Zapisz

Ctrl+X → Y → Enter

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
   Loaded: loaded
   Active: active (running)
```

**Logi na żywo:**
```bash
sudo journalctl -u voice-notes-bot -f
```

(Wyjdź: Ctrl+C)

---

## CZĘŚĆ 10: Zarządzanie botem

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

### Sprawdź logi

```bash
sudo journalctl -u voice-notes-bot -n 50
```

(50 ostatnich linii)

### Aktualizacja kodu

```bash
cd ~/voice-notes-bot
git pull  # lub skopiuj nowe pliki
sudo systemctl restart voice-notes-bot
```

---

## 🔒 Bezpieczeństwo

### 1. Firewall (opcjonalnie)

Bot nie wymaga otwartych portów (komunikuje się z Telegram API outbound), ale możesz dodatkowo zabezpieczyć:

```bash
sudo apt install -y ufw
sudo ufw allow ssh
sudo ufw enable
```

### 2. Automatyczne aktualizacje bezpieczeństwa

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Wybierz: **Yes**

### 3. Backup bazy danych

Regularnie backupuj `voice_notes.db`:

```bash
# Lokalne pobranie bazy
gcloud compute scp voice-notes-bot:~/voice-notes-bot/voice_notes.db ./voice_notes_backup.db
```

**Automatyczny backup (opcjonalnie):**

```bash
# Na VM
crontab -e
```

Dodaj linię (backup codziennie o 3:00):
```
0 3 * * * cp ~/voice-notes-bot/voice_notes.db ~/voice_notes_backup_$(date +\%Y\%m\%d).db
```

---

## 💰 Koszty

### Free Tier (zawsze darmowy)

- **f1-micro VM**: $0/miesiąc (w regionach us-west1, us-central1, us-east1)
- **30 GB Standard Persistent Disk**: $0/miesiąc (w ramach free tier)
- **Egress (outbound traffic)**: 1 GB/miesiąc gratis (potem ~$0.01/GB)

### OpenAI API

- **Whisper**: ~$0.006/minuta nagrania
- **GPT-4o-mini**: ~$0.0001-0.0002/notatka

**Szacunkowy koszt całkowity:** $0-2/miesiąc (50 notatek)

---

## 🐛 Troubleshooting

### Bot się nie uruchamia

1. Sprawdź logi:
   ```bash
   sudo journalctl -u voice-notes-bot -n 100
   ```

2. Sprawdź czy `.env` istnieje:
   ```bash
   cat ~/voice-notes-bot/.env
   ```

3. Sprawdź uprawnienia:
   ```bash
   ls -la ~/voice-notes-bot/
   ```

### VM za wolne / Out of memory

f1-micro ma tylko 614 MB RAM. Jeśli bot crashuje:

1. Dodaj swap:
   ```bash
   sudo fallocate -l 1G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

2. Restart bota:
   ```bash
   sudo systemctl restart voice-notes-bot
   ```

### Nie mogę połączyć się przez SSH

1. W Google Cloud Console → VM instances
2. Sprawdź czy VM jest **Running** (zielona ikona)
3. Kliknij **"SSH"** ponownie
4. Sprawdź firewall rules: VPC network → Firewall → Dodaj regułę dla SSH (port 22)

### Błąd "Permission denied"

```bash
sudo chown -R $USER:$USER ~/voice-notes-bot
chmod 755 ~/voice-notes-bot
```

---

## 📊 Monitoring

### Sprawdź zużycie RAM/CPU

```bash
htop
```

(Instalacja: `sudo apt install htop`)

### Sprawdź rozmiar bazy

```bash
du -h ~/voice-notes-bot/voice_notes.db
```

### Sprawdź uptime VM

```bash
uptime
```

---

## ✅ Gotowe!

Twój bot działa teraz 24/7 na Google Cloud za darmo! 🎉

**Co dalej?**

1. Wyślij voice message na Telegram
2. Sprawdź czy bot odpowiada
3. Używaj i ciesz się automatycznymi notatkami!

**Pytania?** Otwórz issue na GitHubie.

---

## 🔗 Przydatne linki

- Google Cloud Console: https://console.cloud.google.com
- Google Cloud Free Tier: https://cloud.google.com/free
- Telegram BotFather: https://t.me/BotFather
- OpenAI Platform: https://platform.openai.com
- Google Cloud Documentation: https://cloud.google.com/compute/docs

