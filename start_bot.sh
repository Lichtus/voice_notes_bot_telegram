#!/bin/bash
# Skrypt startowy dla Telegram Voice Notes Bot

cd /home/lichtus/Documents/Git/voice_notes_bot/voice_notes_bot_telegram

# Aktywuj wirtualne środowisko
source venv/bin/activate

# Wyświetl header
clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   🎙️  TELEGRAM VOICE NOTES BOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📂 Katalog roboczy: $(pwd)"
echo "📅 Uruchomienie: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔄 Uruchamianie bota..."
echo ""

# Uruchom bota
python bot.py

# Jeśli bot się zamknie, pokaż komunikat
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  Bot został zatrzymany!"
echo "📅 Czas zatrzymania: $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Naciśnij Enter, aby zamknąć..."
