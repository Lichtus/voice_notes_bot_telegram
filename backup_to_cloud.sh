#!/bin/bash
#
# Automatyczny backup bazy danych Voice Notes Bot do Google Cloud Storage
#
# Użycie: ./backup_to_cloud.sh
# Cron: 0 */6 * * * /home/user/voice-notes-bot/backup_to_cloud.sh
#

set -e  # Exit on error

# Konfiguracja
DB_FILE="/home/user/voice-notes-bot/voice_notes.db"
BACKUP_DIR="/home/user/voice-notes-bot/backups"
GCS_BUCKET="gs://voice-notes-backups-$(whoami)"  # Zmień na swoją nazwę bucket
RETENTION_DAYS=30  # Usuń backupy starsze niż 30 dni

# Kolory dla outputu
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="voice_notes_${TIMESTAMP}.db"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

echo -e "${GREEN}🔄 Rozpoczynam backup bazy danych...${NC}"

# 1. Utwórz katalog backupów jeśli nie istnieje
mkdir -p "${BACKUP_DIR}"

# 2. Stwórz lokalny backup z kompresją
echo -e "${YELLOW}📦 Tworzę lokalny backup...${NC}"
if [ -f "${DB_FILE}" ]; then
    # Użyj sqlite3 do stworzenia czystej kopii (unikaj locked database)
    sqlite3 "${DB_FILE}" ".backup ${BACKUP_PATH}"

    # Kompresja
    gzip "${BACKUP_PATH}"
    BACKUP_PATH="${BACKUP_PATH}.gz"

    echo -e "${GREEN}✅ Lokalny backup utworzony: ${BACKUP_NAME}.gz${NC}"
else
    echo -e "${RED}❌ Błąd: Nie znaleziono pliku bazy danych: ${DB_FILE}${NC}"
    exit 1
fi

# 3. Upload do Google Cloud Storage
echo -e "${YELLOW}☁️  Uploading do Cloud Storage...${NC}"
if command -v gsutil &> /dev/null; then
    # Sprawdź czy bucket istnieje, jeśli nie - utwórz
    if ! gsutil ls "${GCS_BUCKET}" &> /dev/null; then
        echo -e "${YELLOW}📦 Tworzę nowy bucket: ${GCS_BUCKET}${NC}"
        gsutil mb -l europe-central2 "${GCS_BUCKET}"

        # Ustaw lifecycle policy (automatyczne usuwanie starych backupów)
        cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": ${RETENTION_DAYS}}
      }
    ]
  }
}
EOF
        gsutil lifecycle set /tmp/lifecycle.json "${GCS_BUCKET}"
        rm /tmp/lifecycle.json
    fi

    # Upload
    gsutil cp "${BACKUP_PATH}" "${GCS_BUCKET}/"
    echo -e "${GREEN}✅ Backup przesłany do Cloud Storage${NC}"
else
    echo -e "${RED}❌ gsutil nie jest zainstalowane. Pomijam upload do cloud.${NC}"
    echo -e "${YELLOW}ℹ️  Instalacja: curl https://sdk.cloud.google.com | bash${NC}"
fi

# 4. Usuń stare lokalne backupy (starsze niż RETENTION_DAYS)
echo -e "${YELLOW}🧹 Czyszczę stare lokalne backupy...${NC}"
find "${BACKUP_DIR}" -name "voice_notes_*.db.gz" -type f -mtime +${RETENTION_DAYS} -delete
echo -e "${GREEN}✅ Stare backupy usunięte${NC}"

# 5. Pokaż statystyki
echo ""
echo -e "${GREEN}📊 STATYSTYKI BACKUP:${NC}"
echo -e "   📁 Rozmiar: $(du -h ${BACKUP_PATH} | cut -f1)"
echo -e "   📅 Data: ${TIMESTAMP}"
echo -e "   💾 Lokalne backupy: $(ls -1 ${BACKUP_DIR}/voice_notes_*.db.gz 2>/dev/null | wc -l)"
echo -e "   ☁️  Cloud backupy: $(gsutil ls ${GCS_BUCKET}/ 2>/dev/null | wc -l)"
echo ""
echo -e "${GREEN}✅ Backup zakończony pomyślnie!${NC}"
