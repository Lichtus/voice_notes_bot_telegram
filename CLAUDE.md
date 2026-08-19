# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot for Polish-language voice notes. Audio → Whisper transcription → GPT-4o-mini structure extraction (topic, description, tasks, key insights, deadlines, category) → SQLite/PostgreSQL. Includes semantic search via embeddings, PDF export, and a separate Flask web app for browsing notes.

Everything user-facing (prompts, log messages, comments, UI text) is in Polish. Keep it that way.

## Running

Docker is the primary way to run this locally:

```bash
docker compose up -d --build          # both services
docker compose logs -f bot            # follow bot logs
docker compose restart bot            # after code changes: up -d --build
docker compose down                   # stop
```

Bare metal (venv) still works and is useful for one-off scripts:

```bash
pip install -r requirements-bot.txt && python bot.py
pip install -r requirements-web.txt && python web_app.py
python init_db.py        # create tables from scratch
python view_database.py  # CLI browser
```

**Only one bot process may poll Telegram at a time** — a second one dies with
`telegram.error.Conflict: terminated by other getUpdates request`. A
`voice-notes-bot.service` systemd unit may still be installed on the host from the
pre-Docker setup; it must stay stopped and disabled while the container runs.

The two setups use **different database files**: systemd/venv uses `./voice_notes.db`,
Docker uses `./data/voice_notes.db` (bind-mounted to `/app/data`). Switching direction
means copying the file across, after a `PRAGMA wal_checkpoint(TRUNCATE)`.

There is no test suite, linter, or formatter configured. Verify changes by running the bot/web app.

`requirements-bot.txt` and `requirements-web.txt` are the only dependency files. Legacy
material — the pre-Telegram Streamlit app, historical migration scripts, venv launchers and
the old deployment guides — was moved out of the repo into a gitignored `archive/` directory
on 2026-08-19; recover anything from git history before that date if needed.

## Architecture

### Two processes, one database

`bot.py` and `web_app.py` are independent processes sharing the same DB file (SQLite WAL mode, `busy_timeout=30000`, `StaticPool`, `check_same_thread=False` — set up in `Database.__init__`). Setting `DATABASE_URL` switches both to PostgreSQL/Supabase instead.

They also talk over HTTP for login: `/start webapp_login` in the bot generates a 6-digit code, shows it to the user, and POSTs it to the web app's `/api/store-code` at `WEB_APP_URL`. The web app holds codes in an **in-memory dict** (`login_codes`), 5-minute TTL — so codes die on web app restart, and the two processes must be able to reach each other. The alternative auth path is the Telegram Login Widget with HMAC verification (`verify_telegram_auth`).

Photos are never stored locally: only Telegram `file_id`s go in the DB (JSON array in `photo_file_ids`), and the web app's `/notes/<id>/photo/<idx>` proxies them live through the Telegram `getFile` API. Note that this route reads the user id from `ALLOWED_USER_IDS[0]` rather than the session — single-user assumption baked in.

### Pipeline (`ai_processor.AIProcessor`)

`process_voice_note()` chains: `transcribe_audio()` (returns `(text, duration_seconds)`) → `extract_structure()` → `get_embedding()` on topic+description, tracking token usage at each step. `cost_calculator.CostCalculator` converts usage to USD.

Two GPT prompts live in `config.py`, both `response_format={"type": "json_object"}`:
- `EXTRACTION_PROMPT` → `temat`, `opis`, `zadania`, `kluczowe_mysli`, `terminy`, `kategoria`, `confidence`
- `DEEP_ANALYSIS_PROMPT` → `tytul`, `uczestnicy`, `sekcje` (with `cytaty`), `ustalenia`, `daty_chronologicznie`, `kluczowe_daty_podsumowanie`

Deep analysis (`analyze_long_note()`) is offered only when total audio exceeds **300 seconds** (`bot.py:762`), via the `ASKING_ANALYSIS` conversation state. Its output lands in the `analiza_*` columns with `czy_analizowane=True`. Both extractors defensively fill missing keys rather than raising, so a malformed GPT response degrades instead of failing.

### Audio handling landmine

Telegram returns voice files with **no extension** in `file_path` (e.g. `voice/file_126`),
while the Whisper endpoint rejects anything it cannot identify by filename. `handle_voice()`
therefore hardcodes `filename="voice.ogg"` and passes it down to `transcribe_audio()`, which
sets it on the `BytesIO` object. Deriving the name from `file_path` instead returns
`400 Unrecognized file format`.

Audio duration is **estimated, not measured**: `len(audio_bytes) / 10000` at
[ai_processor.py:43], assuming ~10 KB/s OGG Opus. That estimate drives both the Whisper cost
figure and the 300-second deep-analysis threshold. Telegram supplies the true value in
`update.message.voice.duration`.

### Bot conversation flow

States: `COLLECTING_AUDIO, WAITING_CONFIRMATION, EDITING_TEMAT, EDITING_OPIS, WAITING_PHOTOS, ASKING_PDF, EDITING_NOTE, ASKING_ANALYSIS` (`EDITING_OPIS` is declared but not wired into any handler).

Flow: voice/audio → optionally more recordings (combined with `[Część N]` markers) → deep-analysis prompt if >5 min → preview → photos → PDF → save.

Two things to respect when touching `main()`:
- `edit_note_conv_handler` **must** be registered before the main `conv_handler` — it claims `^edit_note_` callbacks first.
- Nearly every inline button routes into the single `button_handler` dispatcher (~560 lines, `bot.py:662`), which branches on `query.data` by exact match (`finalize_audio`, `add_photos`, `analysis_yes`, …) or `startswith` prefix (`transcript_`, `download_pdf_`, `play_`, `edit_note_`, `download_transcript_`). New buttons go in that dispatcher, and prefix-based ones also need a `CallbackQueryHandler(..., pattern=...)` registration if they fire outside a conversation.

In-flight note data lives in module-level dicts `pending_notes` and `editing_note_id` keyed by user id — nothing persists across bot restarts mid-conversation.

Voice search is detected by first-word match against `["szukaj", "znajdź", "wyszukaj", "pokaż", "search", "find", "znajdz"]` on the transcription, which diverts to `handle_voice_search()` instead of creating a note.

### Database (`database.py`)

`Notatka` (soft-deleted via `deleted_at`; every read filters `deleted_at.is_(None)`) and `Zadanie`. All access goes through methods on the `Database` class — a single long-lived `self.session`, no per-request scoping.

Conventions that matter:
- **Costs are TEXT columns**, not REAL — SQLite float precision loses sub-cent values. `update_notatka()` accumulates via an internal `add_cost()` that parses, adds, reformats.
- `embedding`, `photo_file_ids`, `kluczowe_mysli`, `terminy`, `analiza_*` are all JSON-in-TEXT.
- `semantic_search()` loads **every** note with an embedding and computes cosine similarity in Python/NumPy. Fine at current scale, linear in note count.
- `update_notatka(zadania_list=...)` **replaces** all tasks rather than merging.

### Migrations

No Alembic. `Base.metadata.create_all()` runs on every startup and creates missing tables
with the **full current schema** — a fresh database needs no migration at all. What it never
does is add a column to a table that already exists, so upgrading an older database means a
hand-written `PRAGMA table_info` → conditional `ALTER TABLE ADD COLUMN` script. The historical
ones live in `archive/`. Adding a column means: update the model, write such a script if any
live database predates it, and update `add_notatka()`/`update_notatka()` plus the display functions (`show_note_preview()`, `send_full_note()`, `send_full_note_from_callback()`, `generate_pdf()`, and the web templates).

### PDF generation

`generate_pdf()` in `bot.py` builds an HTML string inline and renders it with WeasyPrint, embedding photos as base64 data URIs. The web app has its own parallel HTML builder in `generate_email_html()` for the email-export route — the two are not shared, so styling changes need applying in both.

## Docker layout

`Dockerfile` is multi-stage with two targets sharing one code base: `bot` additionally
installs the Pango/Cairo/gdk-pixbuf system libraries and DejaVu/Liberation fonts that
WeasyPrint needs for PDF generation with Polish diacritics; `web` skips them. Both run as
uid/gid 1000 so files written into the `./data` bind mount stay owned by the host user.

Compose overrides two variables from `.env`, because the in-container values differ from
the bare-metal ones: `DATABASE_PATH=/app/data/voice_notes.db` and — for the bot —
`WEB_APP_URL=http://web:5000`, the compose-network hostname the login-code POST targets.

The web port is published on `127.0.0.1:5000` only, since `/notes` and the other view
routes carry no `@login_required`. Change it to `"5000:5000"` to reach it from the LAN,
and add auth first if you do.

Both requirements files carry a dependency that is easy to mistake for dead weight and
drop — each was missing until the container's clean environment exposed it:
`requirements-web.txt` needs `numpy` (`web_app.py` never imports it, but `database.py`
does at module level for `semantic_search()`), and `requirements-bot.txt` needs `requests`
(imported inside `handle_webapp_login()` at [bot.py:62], so the crash only surfaces when a
user actually runs `/start webapp_login`). The shared venv hid both.

## Environment (.env)

```
TELEGRAM_BOT_TOKEN=xxx            # from @BotFather
ALLOWED_USER_IDS=123,456          # whitelist, enforced by @check_user_allowed
OPENAI_API_KEY=sk-xxx
DATABASE_PATH=voice_notes.db      # SQLite path (default)
DATABASE_URL=postgresql://...     # optional: switches to PostgreSQL/Supabase
WEB_SECRET_KEY=xxx                # Flask session secret
WEB_APP_URL=http://localhost:5000 # where the bot POSTs login codes
```

`TELEGRAM_BOT_USERNAME` is hardcoded in `web_app.py` (used by the Telegram Login Widget).

## Changing models or pricing

Model ids live in `config.py` (`WHISPER_MODEL`, `GPT_MODEL`) and `ai_processor.py` (`EMBEDDING_MODEL`). Prices are hardcoded constants in `cost_calculator.py`, current as of December 2025 — update them together with any model change or historical cost figures become inconsistent.

## Repository scope

The repo deliberately holds only what runs the application. Deployment guides (Google Cloud,
Supabase, Linux Mint, cloud backups), venv launcher scripts, the systemd unit and superseded
migration scripts were moved to a gitignored `archive/` directory — they are in git history
up to 2026-08-19 if ever needed.
