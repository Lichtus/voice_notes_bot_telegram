# ☁️ Google Cloud Storage - Setup Backupów

Kompletny przewodnik konfiguracji automatycznych backupów bazy danych SQLite do Google Cloud Storage.

## 📋 Spis Treści

1. [Architektura Rozwiązania](#architektura)
2. [Konfiguracja Google Cloud Storage](#konfiguracja-gcs)
3. [Instalacja na VM](#instalacja-na-vm)
4. [Automatyzacja z Cron](#automatyzacja)
5. [Przywracanie Backupów](#przywracanie)
6. [Monitoring i Koszty](#monitoring)

---

## 🏗️ Architektura

```
┌─────────────────────────────────────────┐
│  Google Compute Engine f1-micro (FREE)  │
│                                         │
│  ┌─────────────────┐                   │
│  │   Bot Process   │                   │
│  │   (systemd)     │                   │
│  └────────┬────────┘                   │
│           │ writes                     │
│           ▼                            │
│  ┌─────────────────┐                   │
│  │ voice_notes.db  │◄───┐              │
│  │    (SQLite)     │    │ backup       │
│  └─────────────────┘    │ (cron)       │
│                         │              │
│  ┌──────────────────────┘              │
│  │ backup_to_cloud.sh                  │
│  └──────────┬──────────────────────────┘
│             │
└─────────────┼──────────────────────────┘
              │ gsutil cp
              ▼
┌──────────────────────────────────────────┐
│   Google Cloud Storage (5GB FREE)       │
│                                          │
│   gs://voice-notes-backups/              │
│   ├── voice_notes_20240115_060000.db.gz │
│   ├── voice_notes_20240115_120000.db.gz │
│   ├── voice_notes_20240115_180000.db.gz │
│   └── ... (auto-delete po 30 dniach)    │
└──────────────────────────────────────────┘
```

**Zalety tego rozwiązania:**
- ✅ **Darmowe** - f1-micro VM + 5GB Cloud Storage w free tier
- ✅ **Automatyczne** - cron co 6h
- ✅ **Bezpieczne** - geograficznie rozproszone (europa-central2)
- ✅ **Proste** - SQLite bez zewnętrznych zależności
- ✅ **Szybkie** - lokalne operacje, brak latency

---

## 🔧 Konfiguracja Google Cloud Storage

### 1. Zaloguj się do Google Cloud (na VM lub lokalnie)

```bash
# Instalacja Google Cloud SDK (jeśli nie ma)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Inicjalizacja
gcloud init

# Zaloguj się
gcloud auth login

# Ustaw projekt
gcloud config set project YOUR_PROJECT_ID
```

### 2. Utwórz Cloud Storage Bucket

```bash
# Nazwa bucket musi być globalnounikalna
BUCKET_NAME="voice-notes-backups-$(whoami)-$(date +%s)"

# Utwórz bucket w regionie europa-central2 (Warszawa)
gsutil mb -l europe-central2 gs://${BUCKET_NAME}

# Ustaw lifecycle policy (auto-delete po 30 dniach)
cat > lifecycle.json <<EOF
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

gsutil lifecycle set lifecycle.json gs://${BUCKET_NAME}
rm lifecycle.json

echo "✅ Bucket utworzony: gs://${BUCKET_NAME}"
```

### 3. Ustaw uprawnienia (opcjonalne - dla bezpieczeństwa)

```bash
# Tylko twój account ma dostęp
gsutil iam ch user:YOUR_EMAIL@gmail.com:objectAdmin gs://${BUCKET_NAME}

# Usuń publiczny dostęp
gsutil iam ch -d allUsers gs://${BUCKET_NAME}
gsutil iam ch -d allAuthenticatedUsers gs://${BUCKET_NAME}
```

---

## 💻 Instalacja na VM

### 1. Przygotuj skrypty backupu

```bash
# Na VM - skopiuj skrypty
cd /home/user/voice-notes-bot

# Nadaj uprawnienia wykonywania
chmod +x backup_to_cloud.sh
chmod +x restore_from_cloud.sh

# Edytuj backup_to_cloud.sh - ustaw swoją nazwę bucket
nano backup_to_cloud.sh
# Zmień linię:
# GCS_BUCKET="gs://voice-notes-backups-twoja-nazwa"
```

### 2. Testuj backup ręcznie

```bash
# Test backupu
./backup_to_cloud.sh

# Sprawdź czy backup jest w cloud
gsutil ls gs://voice-notes-backups-twoja-nazwa/

# Sprawdź lokalne backupy
ls -lh backups/
```

**Spodziewany output:**
```
🔄 Rozpoczynam backup bazy danych...
📦 Tworzę lokalny backup...
✅ Lokalny backup utworzony: voice_notes_20240115_143022.db.gz
☁️  Uploading do Cloud Storage...
✅ Backup przesłany do Cloud Storage

📊 STATYSTYKI BACKUP:
   📁 Rozmiar: 124K
   📅 Data: 20240115_143022
   💾 Lokalne backupy: 3
   ☁️  Cloud backupy: 3

✅ Backup zakończony pomyślnie!
```

---

## ⏰ Automatyzacja z Cron

### 1. Dodaj zadanie Cron (backup co 6h)

```bash
# Edytuj crontab
crontab -e

# Dodaj tę linię (backup o 00:00, 06:00, 12:00, 18:00)
0 */6 * * * /home/user/voice-notes-bot/backup_to_cloud.sh >> /home/user/voice-notes-bot/backup.log 2>&1

# Zapisz i wyjdź (Ctrl+O, Enter, Ctrl+X w nano)
```

### 2. Weryfikacja Cron

```bash
# Sprawdź czy zadanie zostało dodane
crontab -l

# Sprawdź logi backupów
tail -f /home/user/voice-notes-bot/backup.log
```

### 3. Harmonogram backupów

| Czas | Backup | Lokalizacja |
|------|--------|-------------|
| 00:00 | Automatyczny | Local + Cloud Storage |
| 06:00 | Automatyczny | Local + Cloud Storage |
| 12:00 | Automatyczny | Local + Cloud Storage |
| 18:00 | Automatyczny | Local + Cloud Storage |

**Retention:** Backupy starsze niż 30 dni są automatycznie usuwane (lifecycle policy).

---

## 🔄 Przywracanie Backupów

### Scenariusz 1: Lista dostępnych backupów

```bash
./restore_from_cloud.sh
```

Output:
```
📋 DOSTĘPNE BACKUPY:

☁️  Cloud Storage (gs://voice-notes-backups-xyz):
   voice_notes_20240115_060000.db.gz (124 KB)
   voice_notes_20240115_120000.db.gz (125 KB)
   voice_notes_20240115_180000.db.gz (126 KB)

💾 Lokalne (/home/user/voice-notes-bot/backups):
   voice_notes_20240115_060000.db.gz (124K)
   voice_notes_20240115_120000.db.gz (125K)

Użycie: ./restore_from_cloud.sh <nazwa_backupu>
```

### Scenariusz 2: Przywróć konkretny backup

```bash
# Zatrzymaj bota
sudo systemctl stop voice-notes-bot

# Przywróć backup
./restore_from_cloud.sh voice_notes_20240115_120000.db.gz

# Uruchom bota
sudo systemctl start voice-notes-bot
```

Output:
```
🔄 Przywracam backup: voice_notes_20240115_120000.db.gz

💾 Tworzę safety backup obecnej bazy
📦 Rozpakowuję i przywracam bazę...
✅ Baza danych przywrócona pomyślnie!

📊 STATYSTYKI PRZYWRÓCONEJ BAZY:
   📝 Notatki: 47
   📋 Zadania: 23

✅ Możesz uruchomić bota: python bot.py
```

### Scenariusz 3: Disaster Recovery (awaria VM)

Jeśli cała VM zostanie zniszczona:

```bash
# 1. Utwórz nową VM (patrz GOOGLE_CLOUD_SETUP.md)

# 2. Zainstaluj aplikację
git clone https://github.com/your-repo/voice-notes-bot
cd voice-notes-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements-bot.txt

# 3. Skonfiguruj .env
cp .env.example .env
nano .env  # Ustaw tokeny

# 4. Zaloguj się do gcloud
gcloud auth login

# 5. Lista backupów
gsutil ls gs://voice-notes-backups-xyz/

# 6. Pobierz najnowszy backup
gsutil cp gs://voice-notes-backups-xyz/voice_notes_LATEST.db.gz .
gunzip voice_notes_LATEST.db.gz
mv voice_notes_LATEST.db voice_notes.db

# 7. Uruchom bota
python bot.py
```

---

## 📊 Monitoring i Koszty

### Monitoring Backupów

**Sprawdź ostatni backup:**
```bash
# Cloud Storage
gsutil ls -l gs://voice-notes-backups-xyz/ | tail -5

# Lokalnie
ls -lht backups/ | head -5

# Logi cron
tail -n 50 backup.log
```

**Rozmiar backupów:**
```bash
# Cloud Storage (total)
gsutil du -sh gs://voice-notes-backups-xyz/

# Lokalne
du -sh backups/
```

### Koszty (Google Cloud Free Tier)

| Zasób | Limit Free Tier | Twoje Użycie | Koszt |
|-------|-----------------|--------------|-------|
| **f1-micro VM** | 1 instance (us-west1, us-central1, us-east1) | 1 instance | **$0/mies** |
| **Cloud Storage** | 5 GB | ~0.5 GB (backupy) | **$0/mies** |
| **Network Egress** | 1 GB/mies | ~0.1 GB | **$0/mies** |
| **Cloud Storage Operations** | 5000 Class A/50000 Class B | ~120/mies | **$0/mies** |
| **TOTAL** | - | - | **$0/mies** ✅ |

**Uwagi:**
- Backupy SQLite są małe (100-200KB każdy)
- Przy 4 backupach dziennie = ~25 MB/dzień = 750 MB/miesiąc
- Lifecycle policy usuwa stare backupy automatycznie
- Całość zmieści się w 5GB free tier

### Alerty (opcjonalne)

Możesz skonfigurować email alerts w Google Cloud Console:

1. **Cloud Monitoring** → Create Alerting Policy
2. Alert na: "Cloud Storage bucket size > 4.5 GB"
3. Email notification

---

## 🎯 Podsumowanie

**Co masz teraz:**
- ✅ Automatyczne backupy co 6h
- ✅ 30-dniowa retencja backupów
- ✅ Geograficznie rozproszone (Cloud Storage)
- ✅ Łatwe przywracanie (`restore_from_cloud.sh`)
- ✅ Całkowicie darmowe (Free Tier)
- ✅ Safety backups przed każdym restore

**Następne kroki:**
1. Testuj backup ręcznie: `./backup_to_cloud.sh`
2. Skonfiguruj cron: `crontab -e`
3. Zweryfikuj pierwszy automatyczny backup
4. Testuj restore: `./restore_from_cloud.sh`

**W razie problemów:**
- Sprawdź logi: `tail -f backup.log`
- Sprawdź cron: `sudo tail -f /var/log/syslog | grep CRON`
- Testuj gsutil: `gsutil ls gs://voice-notes-backups-xyz/`

---

## 📚 Dodatkowe Zasoby

- [Google Cloud Storage Docs](https://cloud.google.com/storage/docs)
- [SQLite Backup Best Practices](https://www.sqlite.org/backup.html)
- [Cron Tutorial](https://crontab.guru/)

**Autor:** Voice Notes Bot System
**Data:** 2024-01-15
**Wersja:** 1.0
