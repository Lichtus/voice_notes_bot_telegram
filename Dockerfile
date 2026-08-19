# =====================================================================
# Voice Notes Bot — obraz wielostopniowy.
# Dwa targety (bot / web) dzielą kod, ale mają rozdzielne zależności:
# tylko bot generuje PDF-y, więc tylko on ciągnie ciężkie biblioteki
# systemowe WeasyPrint (Pango/Cairo).
# =====================================================================

# ---------- wspólna baza ----------
FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Warsaw

# UID/GID 1000 = użytkownik hosta, żeby pliki bazy w ./data
# nie stawały się własnością roota
RUN groupadd -g 1000 app && useradd -u 1000 -g 1000 -m -s /bin/bash app

WORKDIR /app
RUN mkdir -p /app/data && chown -R app:app /app


# ---------- bot telegramowy ----------
FROM base AS bot

# WeasyPrint 60.2 wymaga Pango/Cairo/gdk-pixbuf; czcionki DejaVu i Liberation
# dają poprawne polskie znaki diakrytyczne w generowanych PDF-ach
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-bot.txt ./
RUN pip install -r requirements-bot.txt

COPY --chown=app:app . .

USER app
CMD ["python", "bot.py"]


# ---------- aplikacja webowa ----------
FROM base AS web

COPY requirements-web.txt ./
RUN pip install -r requirements-web.txt

COPY --chown=app:app . .

USER app
EXPOSE 5000
CMD ["python", "web_app.py"]
