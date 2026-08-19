#!/bin/bash
# Skrypt startowy dla Voice Notes Web App

cd /home/lichtus/Documents/Git/voice_notes_bot/voice_notes_bot_telegram

# Aktywuj wirtualne środowisko
source venv/bin/activate

# Wyświetl header
clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   🌐  VOICE NOTES WEB APPLICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📂 Katalog roboczy: $(pwd)"
echo "📅 Uruchomienie: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "🌐 Aplikacja dostępna pod: http://localhost:5000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔄 Uruchamianie aplikacji webowej..."
echo ""

# Uruchom web app
python web_app.py

# Jeśli aplikacja się zamknie, pokaż komunikat
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  Aplikacja webowa została zatrzymana!"
echo "📅 Czas zatrzymania: $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Naciśnij Enter, aby zamknąć..."
