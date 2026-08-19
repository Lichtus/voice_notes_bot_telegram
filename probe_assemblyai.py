#!/usr/bin/env python3
"""
Porównanie diaryzacji: AssemblyAI kontra gpt-4o-transcribe-diarize.

Puszcza to samo nagranie przez oba systemy i pokazuje sekwencję mówców.
Uruchamiane w kontenerze voice-bot-v2 na bazie testowej.
"""
import os
import sqlite3
import sys
import time

import requests

KLUCZ = os.getenv("ASSEMBLYAI_API_KEY") or os.getenv("ASSEMBLYAI_AP_KEY")
BAZA = "/app/data/voice_notes.db"
API = "https://api.assemblyai.com/v2"


def pobierz_audio(nid):
    tok = os.getenv("TELEGRAM_BOT_TOKEN")
    c = sqlite3.connect(f"file:{BAZA}?mode=ro", uri=True)
    fid, temat = c.execute(
        "select audio_file_id, temat from notatki where id=?", (nid,)).fetchone()
    c.close()
    r = requests.get(f"https://api.telegram.org/bot{tok}/getFile",
                     params={"file_id": fid}, timeout=15).json()
    sciezka = r["result"]["file_path"]
    audio = requests.get(
        f"https://api.telegram.org/file/bot{tok}/{sciezka}", timeout=90).content
    return audio, temat


def assemblyai(audio, jezyk="pl"):
    naglowki = {"authorization": KLUCZ}

    up = requests.post(f"{API}/upload", headers=naglowki, data=audio, timeout=180)
    up.raise_for_status()
    url = up.json()["upload_url"]

    zlec = requests.post(f"{API}/transcript", headers=naglowki, timeout=30, json={
        "audio_url": url,
        "speaker_labels": True,     # diaryzacja — bez żadnych próbek głosu
        "language_code": jezyk,
    })
    zlec.raise_for_status()
    tid = zlec.json()["id"]

    start = time.time()
    while True:
        st = requests.get(f"{API}/transcript/{tid}", headers=naglowki, timeout=30).json()
        if st["status"] == "completed":
            return st, time.time() - start
        if st["status"] == "error":
            raise RuntimeError(st.get("error", "nieznany błąd"))
        time.sleep(3)


def main():
    nid = int(sys.argv[1]) if len(sys.argv) > 1 else 57
    if not KLUCZ:
        print("Brak klucza AssemblyAI w środowisku"); return 1

    audio, temat = pobierz_audio(nid)
    print(f"Notatka #{nid}: {temat}")
    print(f"Audio: {len(audio)//1024} KB\n")

    wynik, czas = assemblyai(audio)
    wypow = wynik.get("utterances") or []
    mowcy = sorted({u["speaker"] for u in wypow})
    czas_audio = (wynik.get("audio_duration") or 0)

    print(f"── AssemblyAI ({czas:.0f}s przetwarzania)")
    print(f"   długość audio : {czas_audio}s")
    print(f"   wypowiedzi    : {len(wypow)}")
    print(f"   mówcy         : {mowcy}")
    print(f"   sekwencja     : {''.join(u['speaker'] for u in wypow)}")
    print(f"   pewność       : {wynik.get('confidence')}")
    print()
    for u in wypow[:6]:
        print(f"   [{u['start']/1000:6.1f}s] Mówca {u['speaker']}: {u['text'][:64]}")
    if len(wypow) > 6:
        print(f"   … jeszcze {len(wypow)-6} wypowiedzi")

    koszt = (czas_audio / 3600) * 0.17
    print(f"\n   koszt tego nagrania: ${koszt:.5f}  (0,15 + 0,02 za diaryzację / godz.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
