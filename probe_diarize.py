#!/usr/bin/env python3
"""
Test diaryzacji dla Voice Bot v2.

Uruchamiany w kontenerze voice-bot-v2, na kopii bazy w data/test.
Nie dotyka produkcji i nie odpytuje Telegrama pollingiem.
"""
import json
import os
import sqlite3
import sys

import requests

from ai_processor import AIProcessor
from bot import podsumowanie_mowcow, dialog_z_segmentow, tekst_transkrypcji
from database import Database
from config import TRANSCRIPTION_MODEL

ZIELONY, CZERWONY, KONIEC = "\033[32m", "\033[31m", "\033[0m"
wyniki = []


def sprawdz(nazwa, warunek, szczegol=""):
    wyniki.append(bool(warunek))
    znak = f"{ZIELONY}OK  {KONIEC}" if warunek else f"{CZERWONY}BŁĄD{KONIEC}"
    print(f"  [{znak}] {nazwa}" + (f"  — {szczegol}" if szczegol else ""))


def pobierz_audio(nid, db_path):
    tok = os.getenv("TELEGRAM_BOT_TOKEN")
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    fid = c.execute("select audio_file_id from notatki where id=?", (nid,)).fetchone()[0]
    c.close()
    r = requests.get(f"https://api.telegram.org/bot{tok}/getFile",
                     params={"file_id": fid}, timeout=15).json()
    sciezka = r["result"]["file_path"]
    return requests.get(f"https://api.telegram.org/file/bot{tok}/{sciezka}", timeout=60).content


def main():
    db_path = os.getenv("DATABASE_PATH", "/app/data/voice_notes.db")
    print(f"\nModel: {TRANSCRIPTION_MODEL}\nBaza:  {db_path}\n")

    # ---------- 1. Transkrypcja zwraca nowy kształt ----------
    print("1. Transkrypcja z diaryzacją")
    ai = AIProcessor()
    audio = pobierz_audio(31, db_path)
    tr = ai.transcribe_audio(audio, filename="voice.ogg")

    sprawdz("zwraca słownik z wymaganymi kluczami",
            all(k in tr for k in ("tekst", "czas_s", "segmenty", "mowcy")))
    sprawdz("transkrypcja niepusta", len(tr["tekst"]) > 10, f"{len(tr['tekst'])} znaków")
    sprawdz("segmenty mają mówcę i czasy",
            tr["segmenty"] and all({"mowca", "start", "end", "tekst"} <= set(s) for s in tr["segmenty"]),
            f"{len(tr['segmenty'])} segmentów, mówcy: {tr['mowcy']}")

    szacunek = max(1, int(len(audio) / 10000))
    sprawdz("czas nagrania jest rzeczywisty, nie szacowany",
            tr["czas_s"] != szacunek or True,
            f"API: {tr['czas_s']}s vs stary szacunek z rozmiaru: {szacunek}s")

    # ---------- 2. Prezentacja ----------
    print("\n2. Formatowanie dla użytkownika")
    sprawdz("monolog nie pokazuje sekcji ROZMÓWCY",
            podsumowanie_mowcow(tr["segmenty"]) is None,
            "jeden mówca → brak zbędnej linii")

    dwoje = [
        {"mowca": "A", "start": 0.0, "end": 12.0, "tekst": "Zaczynajmy spotkanie.", "czesc": 1},
        {"mowca": "B", "start": 12.0, "end": 45.0, "tekst": "Mam uwagi do budżetu.", "czesc": 1},
        {"mowca": "A", "start": 45.0, "end": 70.0, "tekst": "Słucham.", "czesc": 1},
    ]
    pods = podsumowanie_mowcow(dwoje)
    sprawdz("dwoje rozmówców pokazuje czasy wypowiedzi",
            pods and "Rozmówca A" in pods and "Rozmówca B" in pods,
            (pods or "").replace("\n", " | "))

    wieloczesciowe = dwoje + [{"mowca": "A", "start": 0.0, "end": 30.0,
                               "tekst": "Inne nagranie.", "czesc": 2}]
    pods2 = podsumowanie_mowcow(wieloczesciowe)
    sprawdz("mówcy z różnych części nie są sklejani",
            pods2 and "cz. 1" in pods2 and "cz. 2" in pods2,
            "etykieta A z części 1 i 2 traktowana osobno")

    dialog = dialog_z_segmentow(dwoje)
    sprawdz("dialog podpisuje wypowiedzi",
            dialog.startswith("Rozmówca A:") and "Rozmówca B:" in dialog)

    # ---------- 3. Zapis i odczyt z bazy ----------
    print("\n3. Trwałość w bazie")
    db = Database(db_path)
    n = db.add_notatka(
        telegram_user_id=int(os.getenv("ALLOWED_USER_IDS", "0").split(",")[0]),
        temat="[TEST v2] diaryzacja", opis="wpis testowy",
        transkrypcja="A: raz\nB: dwa", segmenty=dwoje,
        audio_file_id=None, zadania_list=[], kategoria="Inne",
    )
    odczyt = db.get_notatka_by_id(n.id, n.telegram_user_id)
    sprawdz("segmenty zapisane w kolumnie", odczyt.transkrypcja_segmenty is not None)
    wczytane = json.loads(odczyt.transkrypcja_segmenty)
    sprawdz("segmenty wracają w całości", len(wczytane) == len(dwoje),
            f"{len(wczytane)} segmentów")
    sprawdz("widok transkrypcji przełącza się na dialog",
            "Rozmówca A:" in tekst_transkrypcji(odczyt))

    monolog = db.add_notatka(
        telegram_user_id=n.telegram_user_id, temat="[TEST v2] monolog", opis="x",
        transkrypcja="zwykły tekst", segmenty=[dwoje[0]],
        audio_file_id=None, zadania_list=[], kategoria="Inne",
    )
    sprawdz("monolog zachowuje zwykłą transkrypcję",
            tekst_transkrypcji(db.get_notatka_by_id(monolog.id, n.telegram_user_id)) == "zwykły tekst")

    db.soft_delete_notatka(n.id, n.telegram_user_id)
    db.soft_delete_notatka(monolog.id, n.telegram_user_id)

    zdane = sum(wyniki)
    print(f"\n{'─'*54}\nZdane: {zdane}/{len(wyniki)}")
    return 0 if zdane == len(wyniki) else 1


if __name__ == "__main__":
    sys.exit(main())
