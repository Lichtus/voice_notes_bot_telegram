#!/bin/bash
#
# Skrypt do przywracania bazy danych z backupu (Cloud Storage lub lokalnego)
#
# Użycie:
#   ./restore_from_cloud.sh                    # Pokazuje dostępne backupy
#   ./restore_from_cloud.sh voice_notes_20240115_120000.db.gz
#

set -e

# Konfiguracja
DB_FILE="/home/user/voice-notes-bot/voice_notes.db"
BACKUP_DIR="/home/user/voice-notes-bot/backups"
GCS_BUCKET="gs://voice-notes-backups-$(whoami)"

# Kolory
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funkcja: Lista dostępnych backupów
list_backups() {
    echo -e "${BLUE}📋 DOSTĘPNE BACKUPY:${NC}\n"

    echo -e "${YELLOW}☁️  Cloud Storage (${GCS_BUCKET}):${NC}"
    if command -v gsutil &> /dev/null; then
        gsutil ls -l "${GCS_BUCKET}/" 2>/dev/null | grep "voice_notes_" || echo "   Brak backupów"
    else
        echo "   gsutil nie zainstalowany"
    fi

    echo ""
    echo -e "${YELLOW}💾 Lokalne (${BACKUP_DIR}):${NC}"
    ls -lh "${BACKUP_DIR}"/voice_notes_*.db.gz 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}' || echo "   Brak backupów"

    echo ""
    echo -e "${GREEN}Użycie:${NC} $0 <nazwa_backupu>"
    echo -e "${GREEN}Przykład:${NC} $0 voice_notes_20240115_120000.db.gz"
}

# Jeśli brak argumentu - pokaż listę
if [ $# -eq 0 ]; then
    list_backups
    exit 0
fi

BACKUP_NAME=$1

echo -e "${YELLOW}🔄 Przywracam backup: ${BACKUP_NAME}${NC}\n"

# 1. Znajdź backup (lokalnie lub w cloud)
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

if [ ! -f "${BACKUP_PATH}" ]; then
    echo -e "${YELLOW}📥 Backup nie znaleziony lokalnie, pobieram z Cloud Storage...${NC}"

    if command -v gsutil &> /dev/null; then
        gsutil cp "${GCS_BUCKET}/${BACKUP_NAME}" "${BACKUP_PATH}"
        echo -e "${GREEN}✅ Pobrano z Cloud Storage${NC}"
    else
        echo -e "${RED}❌ Błąd: Backup nie istnieje lokalnie i gsutil nie jest zainstalowany${NC}"
        exit 1
    fi
fi

# 2. Backup obecnej bazy (safety)
if [ -f "${DB_FILE}" ]; then
    SAFETY_BACKUP="${DB_FILE}.before_restore_$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}💾 Tworzę safety backup obecnej bazy: ${SAFETY_BACKUP}${NC}"
    cp "${DB_FILE}" "${SAFETY_BACKUP}"
fi

# 3. Rozpakuj i przywróć
echo -e "${YELLOW}📦 Rozpakowuję i przywracam bazę...${NC}"

if [[ "${BACKUP_NAME}" == *.gz ]]; then
    gunzip -c "${BACKUP_PATH}" > "${DB_FILE}"
else
    cp "${BACKUP_PATH}" "${DB_FILE}"
fi

# 4. Weryfikacja
if sqlite3 "${DB_FILE}" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo -e "${GREEN}✅ Baza danych przywrócona pomyślnie!${NC}"

    # Statystyki
    echo ""
    echo -e "${BLUE}📊 STATYSTYKI PRZYWRÓCONEJ BAZY:${NC}"
    NOTATKI_COUNT=$(sqlite3 "${DB_FILE}" "SELECT COUNT(*) FROM notatki;")
    ZADANIA_COUNT=$(sqlite3 "${DB_FILE}" "SELECT COUNT(*) FROM zadania;")
    echo -e "   📝 Notatki: ${NOTATKI_COUNT}"
    echo -e "   📋 Zadania: ${ZADANIA_COUNT}"
    echo ""
    echo -e "${GREEN}✅ Możesz uruchomić bota: python bot.py${NC}"
else
    echo -e "${RED}❌ BŁĄD: Przywrócona baza jest uszkodzona!${NC}"
    if [ -f "${SAFETY_BACKUP}" ]; then
        echo -e "${YELLOW}🔄 Przywracam poprzednią wersję...${NC}"
        mv "${SAFETY_BACKUP}" "${DB_FILE}"
        echo -e "${GREEN}✅ Poprzednia wersja przywrócona${NC}"
    fi
    exit 1
fi
