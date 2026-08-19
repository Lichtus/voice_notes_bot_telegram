#!/usr/bin/env python3
"""
Kopia zapasowa bazy notatek.

Tworzy spójną migawkę bazy (VACUUM INTO), weryfikuje ją, eksportuje treść
do JSON-a i usuwa przeterminowane kopie.

Uruchamiany z crona na hoście — celowo nie zależy od Dockera, żeby backup
działał także wtedy, gdy kontenery stoją.

    python3 backup.py [ścieżka_do_bazy]

Domyślnie bierze data/voice_notes.db, czyli plik montowany do kontenerów.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta

# Baza używana przez kontenery. NIE bierzemy DATABASE_PATH z .env, bo tam
# jest ścieżka dla uruchomienia poza Dockerem i wskazuje na nieaktualną kopię.
DOMYSLNA_BAZA = "data/voice_notes.db"
KATALOG_KOPII = "data/backup"
DNI_PRZECHOWYWANIA = 14


def loguj(msg):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}", flush=True)


def zrob_migawke(zrodlo, cel):
    """Spójna kopia działającej bazy. VACUUM INTO obejmuje też zawartość WAL."""
    conn = sqlite3.connect(f"file:{zrodlo}?mode=ro", uri=True)
    try:
        conn.execute("VACUUM INTO ?", (cel,))
    finally:
        conn.close()


def sprawdz(kopia):
    """Kopia, której nie da się odczytać, jest gorsza niż jej brak."""
    conn = sqlite3.connect(f"file:{kopia}?mode=ro", uri=True)
    try:
        wynik = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if wynik != "ok":
            raise RuntimeError(f"integrity_check zwrócił: {wynik}")
        return conn.execute("select count(*) from notatki").fetchone()[0]
    finally:
        conn.close()


def eksportuj_json(kopia, cel):
    """
    Eksport niezależny od SQLite — dane czytelne dowolnym narzędziem.

    Pomija embeddingi (są w pliku .db, a w JSON-ie zajmowałyby wielokrotnie
    więcej niż reszta i czyniły go nieczytelnym; można je odtworzyć z tekstu).
    Zachowuje natomiast audio_file_id i photo_file_ids — dzięki temu zostaje
    otwarta droga do pobrania nagrań i zdjęć z Telegrama w przyszłości.
    """
    conn = sqlite3.connect(f"file:{kopia}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        kolumny = [k[1] for k in conn.execute("PRAGMA table_info(notatki)")
                   if k[1] != "embedding"]
        notatki = []
        for w in conn.execute(f"select {','.join(kolumny)} from notatki order by id"):
            n = dict(w)
            n["zadania"] = [dict(z) for z in conn.execute(
                "select id, zadanie, wykonane, data_wykonania from zadania "
                "where notatka_id = ? order by id", (n["id"],))]
            notatki.append(n)
    finally:
        conn.close()

    with open(cel, "w", encoding="utf-8") as f:
        json.dump({
            "wyeksportowano": datetime.now().isoformat(timespec="seconds"),
            "zrodlo": os.path.basename(kopia),
            "liczba_notatek": len(notatki),
            "uwaga": "Embeddingi pominięte — są w pliku .db. Pola audio_file_id "
                     "i photo_file_ids pozwalają pobrać multimedia z Telegrama.",
            "notatki": notatki,
        }, f, ensure_ascii=False, indent=2, default=str)
    return len(notatki)


def posprzataj():
    """
    Zostawia kopie z ostatnich DNI_PRZECHOWYWANIA dni oraz — bezterminowo —
    kopie z pierwszego dnia każdego miesiąca. Uszkodzenie zauważone po kilku
    miesiącach nadal ma z czego zostać cofnięte.
    """
    granica = datetime.now() - timedelta(days=DNI_PRZECHOWYWANIA)
    usuniete = 0
    for plik in sorted(os.listdir(KATALOG_KOPII)):
        if not plik.startswith("voice_notes-"):
            continue
        try:
            data = datetime.strptime(plik.split("voice_notes-")[1][:10], "%Y-%m-%d")
        except ValueError:
            continue
        if data >= granica or data.day == 1:
            continue
        os.remove(os.path.join(KATALOG_KOPII, plik))
        usuniete += 1
    return usuniete


def main():
    zrodlo = sys.argv[1] if len(sys.argv) > 1 else DOMYSLNA_BAZA

    if not os.path.exists(zrodlo):
        loguj(f"BŁĄD: baza {zrodlo} nie istnieje")
        return 1

    os.makedirs(KATALOG_KOPII, exist_ok=True)
    znacznik = datetime.now().strftime("%Y-%m-%d")
    kopia = os.path.join(KATALOG_KOPII, f"voice_notes-{znacznik}.db")
    eksport = os.path.join(KATALOG_KOPII, f"voice_notes-{znacznik}.json")

    if os.path.exists(kopia):
        os.remove(kopia)   # VACUUM INTO odmawia nadpisania istniejącego pliku

    try:
        zrob_migawke(zrodlo, kopia)
        liczba = sprawdz(kopia)
        wyeksportowano = eksportuj_json(kopia, eksport)
    except Exception as e:
        loguj(f"BŁĄD: {type(e).__name__}: {e}")
        return 1

    rozmiar = os.path.getsize(kopia) / 1024
    usuniete = posprzataj()
    loguj(f"OK: {liczba} notatek, {rozmiar:.0f} KB, JSON {wyeksportowano} notatek"
          + (f", usunięto {usuniete} starych kopii" if usuniete else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
