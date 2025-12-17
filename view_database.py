#!/usr/bin/env python3
"""
Prosty skrypt do przeglądania bazy danych Voice Notes Bot
"""
from database import Database
from datetime import datetime

def main():
    from database import Notatka, Zadanie

    db = Database()

    print("=" * 80)
    print("📚 BAZA DANYCH - NOTATKI")
    print("=" * 80)

    # Pobierz wszystkie notatki
    notatki = db.session.query(Notatka).order_by(Notatka.data_utworzenia.desc()).all()

    if not notatki:
        print("\n❌ Brak notatek w bazie!\n")
        return

    print(f"\n📊 Znaleziono: {len(notatki)} notatek\n")

    for i, notatka in enumerate(notatki, 1):
        print(f"\n{'─' * 80}")
        print(f"🆔 ID: {notatka.id}")
        print(f"📅 Data: {notatka.data_utworzenia.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"👤 User ID: {notatka.telegram_user_id}")
        print(f"📌 TEMAT: {notatka.temat}")
        print(f"\n📝 OPIS:")
        print(f"   {notatka.opis}")

        if notatka.transkrypcja:
            print(f"\n🎤 TRANSKRYPCJA:")
            print(f"   {notatka.transkrypcja[:200]}{'...' if len(notatka.transkrypcja) > 200 else ''}")

        # Pokaż zadania
        if notatka.zadania:
            print(f"\n📋 ZADANIA ({len(notatka.zadania)}):")
            for zadanie in notatka.zadania:
                status = "✅" if zadanie.wykonane else "⬜"
                print(f"   {status} [{zadanie.id}] {zadanie.zadanie}")
                if zadanie.wykonane and zadanie.data_wykonania:
                    print(f"       Wykonano: {zadanie.data_wykonania.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"\n📋 ZADANIA: brak")

    print(f"\n{'=' * 80}")

    # Statystyki
    print("\n📊 STATYSTYKI:")
    wszystkie_zadania = db.session.query(Zadanie).all()
    wykonane = sum(1 for z in wszystkie_zadania if z.wykonane)

    print(f"   📝 Notatki: {len(notatki)}")
    print(f"   📋 Zadania wszystkie: {len(wszystkie_zadania)}")
    print(f"   ✅ Wykonane: {wykonane}")
    print(f"   ⬜ Do zrobienia: {len(wszystkie_zadania) - wykonane}")
    print()

    db.close()

if __name__ == "__main__":
    main()
