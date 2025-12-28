# 🌐 Aplikacja Webowa - Voice Notes Bot

Prosta aplikacja webowa do przeglądania notatek głosowych z bazy danych.

## ✨ Funkcje

- ✅ Lista wszystkich notatek (z paginacją)
- ✅ Szczegóły notatki (temat, opis, zadania, transkrypcja)
- ✅ Wyświetlanie zdjęć z Telegram
- ✅ Responsywny design (działa na telefonie i komputerze)
- ✅ Brak konieczności logowania

## 📦 Instalacja

### 1. Zainstaluj zależności

```bash
cd ~/Dokumenty/Git/voice_notes_bot/voice_notes_bot_telegram

# Aktywuj venv
source venv/bin/activate

# Zainstaluj pakiety dla web app
pip install -r requirements-web.txt
```

### 2. Konfiguracja (opcjonalna)

Aplikacja używa tego samego pliku `.env` co bot. Nie musisz nic zmieniać!

## 🚀 Uruchomienie

### Metoda 1: Bezpośrednio (do testowania)

```bash
source venv/bin/activate
python web_app.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:5000`

### Metoda 2: Jako systemd service (produkcja)

Stwórz plik `/etc/systemd/system/voice-notes-web.service`:

```ini
[Unit]
Description=Voice Notes Web Application
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/voice-notes-bot
Environment="PATH=/home/YOUR_USERNAME/voice-notes-bot/venv/bin"
ExecStart=/home/YOUR_USERNAME/voice-notes-bot/venv/bin/python web_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Aktywuj service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-notes-web
sudo systemctl start voice-notes-web

# Sprawdź status
sudo systemctl status voice-notes-web
```

### Metoda 3: Za pomocą Gunicorn (produkcja, wydajność)

Zainstaluj Gunicorn:

```bash
pip install gunicorn
```

Uruchom:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
```

Lub dodaj do systemd:

```ini
ExecStart=/home/YOUR_USERNAME/voice-notes-bot/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
```

## 🌍 Dostęp z Internetu

### Opcja 1: Ngrok (szybki test)

```bash
# Zainstaluj ngrok
snap install ngrok

# Uruchom tunel
ngrok http 5000
```

Otrzymasz publiczny URL typu: `https://abc123.ngrok.io`

### Opcja 2: Reverse Proxy (Nginx)

Konfiguracja Nginx:

```nginx
server {
    listen 80;
    server_name twoja-domena.pl;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Opcja 3: Cloudflare Tunnel (bezpłatny HTTPS)

```bash
# Zainstaluj cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Uruchom tunel
cloudflared tunnel --url http://localhost:5000
```

## 📱 Dostęp tylko w sieci lokalnej

Jeśli chcesz aby aplikacja była dostępna tylko w Twojej sieci lokalnej:

1. Uruchom aplikację
2. Sprawdź swoje lokalne IP: `hostname -I`
3. Otwórz w przeglądarce: `http://192.168.X.X:5000`

## 🔒 Bezpieczeństwo

**UWAGA:** Ta wersja **NIE MA** logowania - każdy kto zna adres URL może przeglądać notatki!

Jeśli chcesz zabezpieczyć aplikację:

1. **Dodaj autentykację** - użyj Flask-Login
2. **Użyj HTTPS** - Cloudflare Tunnel lub Let's Encrypt
3. **Ogranicz dostęp** - firewall / VPN

## 🐛 Troubleshooting

### Błąd: "ModuleNotFoundError: No module named 'flask'"

```bash
source venv/bin/activate
pip install -r requirements-web.txt
```

### Błąd: "Address already in use"

Port 5000 jest zajęty. Zmień port:

```python
# W web_app.py
app.run(host='0.0.0.0', port=5001, debug=True)
```

### Zdjęcia się nie ładują

Sprawdź czy `TELEGRAM_BOT_TOKEN` w `.env` jest poprawny:

```bash
cat .env | grep TELEGRAM_BOT_TOKEN
```

## 🎨 Customizacja

### Zmiana kolorów

Edytuj `static/style.css`:

```css
/* Zmień gradient tła */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Zmiana liczby notatek na stronę

W `web_app.py`:

```python
per_page = 20  # Zmień na dowolną liczbę
```

## 📚 Struktura plików

```
voice-notes-bot/
├── web_app.py              # Główna aplikacja Flask
├── requirements-web.txt    # Zależności dla web app
├── templates/
│   ├── notes_list.html     # Lista notatek
│   └── note_detail.html    # Szczegóły notatki
└── static/
    └── style.css           # CSS styling
```

## 🎉 Gotowe!

Aplikacja webowa jest gotowa do użycia. Możesz teraz przeglądać swoje notatki w przeglądarce!

---

**Autor:** Voice Notes Bot System
**Data:** 2025-12-28
**Wersja:** 1.0 - Web App (Read-Only)
