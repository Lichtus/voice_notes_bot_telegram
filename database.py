"""
Moduł obsługi bazy danych (SQLite lub PostgreSQL/Supabase) dla Voice Notes Bot
"""
import json
import logging
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import DATABASE_PATH, DATABASE_URL

logger = logging.getLogger(__name__)

Base = declarative_base()


class Notatka(Base):
    """Model notatki głosowej"""
    __tablename__ = 'notatki'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(Integer, nullable=False)
    data_utworzenia = Column(DateTime, default=datetime.now, nullable=False)
    temat = Column(String(255), nullable=False)
    opis = Column(Text)
    transkrypcja = Column(Text)
    audio_file_id = Column(Text)  # Telegram file_id
    photo_file_ids = Column(Text)  # JSON array z Telegram file_id zdjęć
    embedding = Column(Text)  # JSON embedding dla semantic search

    # Kolumny kosztów API OpenAI
    audio_duration_seconds = Column(Integer, nullable=True)  # Długość audio w sekundach
    tokens_input = Column(Integer, nullable=True)  # Tokeny wejściowe GPT
    tokens_output = Column(Integer, nullable=True)  # Tokeny wyjściowe GPT
    tokens_embedding = Column(Integer, nullable=True)  # Tokeny embedding
    cost_whisper_usd = Column(Text, nullable=True)  # Koszt Whisper w USD (TEXT aby uniknąć problemów z REAL)
    cost_gpt_input_usd = Column(Text, nullable=True)  # Koszt GPT input w USD
    cost_gpt_output_usd = Column(Text, nullable=True)  # Koszt GPT output w USD
    cost_embedding_usd = Column(Text, nullable=True)  # Koszt embedding w USD
    cost_total_usd = Column(Text, nullable=True)  # Łączny koszt w USD

    # Relacja do zadań
    zadania = relationship("Zadanie", back_populates="notatka", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Notatka(id={self.id}, temat='{self.temat}', data={self.data_utworzenia})>"


class Zadanie(Base):
    """Model zadania związanego z notatką"""
    __tablename__ = 'zadania'

    id = Column(Integer, primary_key=True, autoincrement=True)
    notatka_id = Column(Integer, ForeignKey('notatki.id'), nullable=False)
    zadanie = Column(Text, nullable=False)
    wykonane = Column(Boolean, default=False)
    data_wykonania = Column(DateTime, nullable=True)

    # Relacja do notatki
    notatka = relationship("Notatka", back_populates="zadania")

    def __repr__(self):
        status = "✅" if self.wykonane else "⬜"
        return f"<Zadanie(id={self.id}, {status} '{self.zadanie}')>"


class Database:
    """Klasa zarządzająca bazą danych (SQLite lub PostgreSQL/Supabase)"""

    def __init__(self, db_path=DATABASE_PATH):
        # Jeśli DATABASE_URL jest ustawione - użyj PostgreSQL (Supabase)
        # Jeśli nie - użyj lokalnego SQLite
        if DATABASE_URL:
            # PostgreSQL / Supabase
            self.engine = create_engine(DATABASE_URL, echo=False)
            self.db_type = "postgresql"
            logger.info("💾 Używam bazy danych: PostgreSQL (Supabase)")
        else:
            # SQLite (lokalny plik)
            self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
            self.db_type = "sqlite"
            logger.info(f"💾 Używam bazy danych: SQLite ({db_path})")

        # Utwórz tabele jeśli nie istnieją
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_notatka(self, telegram_user_id, temat, opis, transkrypcja, audio_file_id, zadania_list=None, embedding_vector=None, photo_file_ids=None, cost_data=None):
        """
        Dodaje nową notatkę do bazy

        Args:
            telegram_user_id: ID użytkownika Telegram
            temat: Tytuł notatki
            opis: Szczegółowy opis
            transkrypcja: Pełna transkrypcja audio
            audio_file_id: ID pliku audio w Telegram
            zadania_list: Lista zadań (strings)
            embedding_vector: Wektor embedding dla semantic search (list)
            photo_file_ids: Lista Telegram file_id zdjęć (strings)
            cost_data: Dict z danymi o kosztach API {
                "audio_duration_seconds": int,
                "tokens_input": int,
                "tokens_output": int,
                "tokens_embedding": int,
                "cost_whisper_usd": float,
                "cost_gpt_input_usd": float,
                "cost_gpt_output_usd": float,
                "cost_embedding_usd": float,
                "cost_total_usd": float
            }

        Returns:
            Notatka: Utworzona notatka
        """
        # Serializuj embedding do JSON jeśli podany
        embedding_json = None
        if embedding_vector:
            embedding_json = json.dumps(embedding_vector)

        # Serializuj photo_file_ids do JSON jeśli podane
        photos_json = None
        if photo_file_ids:
            photos_json = json.dumps(photo_file_ids)

        # Przygotuj dane kosztów (konwertuj float na string dla SQLite)
        cost_kwargs = {}
        if cost_data:
            cost_kwargs = {
                "audio_duration_seconds": cost_data.get("audio_duration_seconds"),
                "tokens_input": cost_data.get("tokens_input"),
                "tokens_output": cost_data.get("tokens_output"),
                "tokens_embedding": cost_data.get("tokens_embedding"),
                "cost_whisper_usd": str(cost_data.get("cost_whisper_usd", 0)),
                "cost_gpt_input_usd": str(cost_data.get("cost_gpt_input_usd", 0)),
                "cost_gpt_output_usd": str(cost_data.get("cost_gpt_output_usd", 0)),
                "cost_embedding_usd": str(cost_data.get("cost_embedding_usd", 0)),
                "cost_total_usd": str(cost_data.get("cost_total_usd", 0)),
            }

        notatka = Notatka(
            telegram_user_id=telegram_user_id,
            temat=temat,
            opis=opis,
            transkrypcja=transkrypcja,
            audio_file_id=audio_file_id,
            photo_file_ids=photos_json,
            embedding=embedding_json,
            **cost_kwargs
        )

        # Dodaj zadania jeśli są
        if zadania_list:
            for zadanie_text in zadania_list:
                if zadanie_text.strip():  # Ignoruj puste
                    zadanie = Zadanie(zadanie=zadanie_text.strip())
                    notatka.zadania.append(zadanie)

        self.session.add(notatka)
        self.session.commit()
        return notatka

    def update_notatka(self, notatka_id, telegram_user_id, temat=None, opis=None, transkrypcja=None,
                       zadania_list=None, embedding_vector=None, additional_cost_data=None):
        """
        Aktualizuje istniejącą notatkę

        Args:
            notatka_id: ID notatki do aktualizacji
            telegram_user_id: ID użytkownika (weryfikacja)
            temat: Nowy temat (jeśli None - bez zmian)
            opis: Nowy opis (jeśli None - bez zmian)
            transkrypcja: Nowa transkrypcja (jeśli None - bez zmian)
            zadania_list: Nowa lista zadań - ZASTĘPUJE stare zadania
            embedding_vector: Nowy wektor embedding
            additional_cost_data: Dict z dodatkowymi kosztami do dodania {
                "audio_duration_seconds": int,  # będzie dodane do obecnego
                "tokens_input": int,  # będzie dodane
                "tokens_output": int,  # będzie dodane
                "tokens_embedding": int,  # będzie dodane
                "cost_whisper_usd": float,  # będzie dodane
                "cost_gpt_input_usd": float,  # będzie dodane
                "cost_gpt_output_usd": float,  # będzie dodane
                "cost_embedding_usd": float,  # będzie dodane
                "cost_total_usd": float  # będzie przeliczone
            }

        Returns:
            Notatka: Zaktualizowana notatka lub None jeśli nie znaleziono
        """
        notatka = self.get_notatka_by_id(notatka_id, telegram_user_id)

        if not notatka:
            return None

        # Aktualizuj podstawowe pola
        if temat is not None:
            notatka.temat = temat
        if opis is not None:
            notatka.opis = opis
        if transkrypcja is not None:
            notatka.transkrypcja = transkrypcja

        # Aktualizuj embedding
        if embedding_vector is not None:
            notatka.embedding = json.dumps(embedding_vector)

        # Aktualizuj zadania - ZASTĘPUJEMY wszystkie zadania
        if zadania_list is not None:
            # Usuń stare zadania
            for zadanie in notatka.zadania:
                self.session.delete(zadanie)

            # Dodaj nowe zadania
            for zadanie_text in zadania_list:
                if zadanie_text.strip():
                    zadanie = Zadanie(zadanie=zadanie_text.strip())
                    notatka.zadania.append(zadanie)

        # Aktualizuj koszty - DODAJEMY do istniejących
        if additional_cost_data:
            # Dodaj czas audio
            if additional_cost_data.get("audio_duration_seconds"):
                current_duration = notatka.audio_duration_seconds or 0
                notatka.audio_duration_seconds = current_duration + additional_cost_data["audio_duration_seconds"]

            # Dodaj tokeny
            if additional_cost_data.get("tokens_input"):
                current_tokens = notatka.tokens_input or 0
                notatka.tokens_input = current_tokens + additional_cost_data["tokens_input"]

            if additional_cost_data.get("tokens_output"):
                current_tokens = notatka.tokens_output or 0
                notatka.tokens_output = current_tokens + additional_cost_data["tokens_output"]

            if additional_cost_data.get("tokens_embedding"):
                current_tokens = notatka.tokens_embedding or 0
                notatka.tokens_embedding = current_tokens + additional_cost_data["tokens_embedding"]

            # Dodaj koszty
            def add_cost(current_str, additional):
                current = float(current_str) if current_str else 0.0
                return str(round(current + additional, 6))

            if additional_cost_data.get("cost_whisper_usd") is not None:
                notatka.cost_whisper_usd = add_cost(notatka.cost_whisper_usd, additional_cost_data["cost_whisper_usd"])

            if additional_cost_data.get("cost_gpt_input_usd") is not None:
                notatka.cost_gpt_input_usd = add_cost(notatka.cost_gpt_input_usd, additional_cost_data["cost_gpt_input_usd"])

            if additional_cost_data.get("cost_gpt_output_usd") is not None:
                notatka.cost_gpt_output_usd = add_cost(notatka.cost_gpt_output_usd, additional_cost_data["cost_gpt_output_usd"])

            if additional_cost_data.get("cost_embedding_usd") is not None:
                notatka.cost_embedding_usd = add_cost(notatka.cost_embedding_usd, additional_cost_data["cost_embedding_usd"])

            # Przelicz całkowity koszt
            total = (
                (float(notatka.cost_whisper_usd) if notatka.cost_whisper_usd else 0.0) +
                (float(notatka.cost_gpt_input_usd) if notatka.cost_gpt_input_usd else 0.0) +
                (float(notatka.cost_gpt_output_usd) if notatka.cost_gpt_output_usd else 0.0) +
                (float(notatka.cost_embedding_usd) if notatka.cost_embedding_usd else 0.0)
            )
            notatka.cost_total_usd = str(round(total, 6))

        self.session.commit()
        return notatka

    def get_notatka_by_id(self, notatka_id, telegram_user_id):
        """
        Pobiera notatkę po ID (z weryfikacją użytkownika)

        Args:
            notatka_id: ID notatki
            telegram_user_id: ID użytkownika (weryfikacja)

        Returns:
            Notatka lub None jeśli nie znaleziono
        """
        return self.session.query(Notatka)\
            .filter(
                Notatka.id == notatka_id,
                Notatka.telegram_user_id == telegram_user_id
            ).first()

    def get_notatki(self, telegram_user_id, limit=10):
        """
        Pobiera ostatnie notatki użytkownika

        Args:
            telegram_user_id: ID użytkownika
            limit: Maksymalna liczba notatek

        Returns:
            Lista notatek
        """
        return self.session.query(Notatka)\
            .filter(Notatka.telegram_user_id == telegram_user_id)\
            .order_by(Notatka.data_utworzenia.desc())\
            .limit(limit)\
            .all()

    def search_notatki(self, telegram_user_id, query):
        """
        Wyszukuje notatki po słowach kluczowych

        Args:
            telegram_user_id: ID użytkownika
            query: Szukana fraza

        Returns:
            Lista notatek
        """
        return self.session.query(Notatka)\
            .filter(
                Notatka.telegram_user_id == telegram_user_id,
                (Notatka.temat.contains(query) |
                 Notatka.opis.contains(query) |
                 Notatka.transkrypcja.contains(query))
            )\
            .order_by(Notatka.data_utworzenia.desc())\
            .all()

    def get_wszystkie_zadania(self, telegram_user_id, tylko_niewykonane=True):
        """
        Pobiera wszystkie zadania użytkownika

        Args:
            telegram_user_id: ID użytkownika
            tylko_niewykonane: Czy pokazać tylko niewykonane

        Returns:
            Lista zadań
        """
        query = self.session.query(Zadanie)\
            .join(Notatka)\
            .filter(Notatka.telegram_user_id == telegram_user_id)

        if tylko_niewykonane:
            query = query.filter(Zadanie.wykonane == False)

        return query.order_by(Zadanie.id).all()

    def oznacz_zadanie_wykonane(self, zadanie_id, telegram_user_id):
        """
        Oznacza zadanie jako wykonane

        Args:
            zadanie_id: ID zadania
            telegram_user_id: ID użytkownika (weryfikacja)

        Returns:
            True jeśli sukces, False jeśli nie znaleziono
        """
        zadanie = self.session.query(Zadanie)\
            .join(Notatka)\
            .filter(
                Zadanie.id == zadanie_id,
                Notatka.telegram_user_id == telegram_user_id
            ).first()

        if zadanie:
            zadanie.wykonane = True
            zadanie.data_wykonania = datetime.now()
            self.session.commit()
            return True
        return False

    def get_statystyki(self, telegram_user_id):
        """
        Zwraca statystyki użytkownika

        Returns:
            Dict ze statystykami
        """
        liczba_notatek = self.session.query(Notatka)\
            .filter(Notatka.telegram_user_id == telegram_user_id)\
            .count()

        liczba_zadan = self.session.query(Zadanie)\
            .join(Notatka)\
            .filter(Notatka.telegram_user_id == telegram_user_id)\
            .count()

        liczba_wykonanych = self.session.query(Zadanie)\
            .join(Notatka)\
            .filter(
                Notatka.telegram_user_id == telegram_user_id,
                Zadanie.wykonane == True
            ).count()

        # Oblicz koszty API
        cost_stats = self.get_cost_statistics(telegram_user_id)

        return {
            "notatki": liczba_notatek,
            "zadania_wszystkie": liczba_zadan,
            "zadania_wykonane": liczba_wykonanych,
            "zadania_do_zrobienia": liczba_zadan - liczba_wykonanych,
            "koszty": cost_stats
        }

    def get_cost_statistics(self, telegram_user_id):
        """
        Oblicza statystyki kosztów API dla użytkownika

        Args:
            telegram_user_id: ID użytkownika

        Returns:
            Dict ze statystykami kosztów
        """
        notatki = self.session.query(Notatka)\
            .filter(Notatka.telegram_user_id == telegram_user_id)\
            .all()

        total_whisper = 0.0
        total_gpt_input = 0.0
        total_gpt_output = 0.0
        total_embedding = 0.0
        total_cost = 0.0
        notes_with_costs = 0

        for nota in notatki:
            if nota.cost_total_usd:
                notes_with_costs += 1
                try:
                    total_whisper += float(nota.cost_whisper_usd or 0)
                    total_gpt_input += float(nota.cost_gpt_input_usd or 0)
                    total_gpt_output += float(nota.cost_gpt_output_usd or 0)
                    total_embedding += float(nota.cost_embedding_usd or 0)
                    total_cost += float(nota.cost_total_usd or 0)
                except (ValueError, TypeError):
                    continue

        avg_cost = total_cost / notes_with_costs if notes_with_costs > 0 else 0

        return {
            "total_usd": round(total_cost, 4),
            "total_whisper_usd": round(total_whisper, 4),
            "total_gpt_usd": round(total_gpt_input + total_gpt_output, 4),
            "total_embedding_usd": round(total_embedding, 4),
            "average_per_note_usd": round(avg_cost, 4),
            "notes_with_costs": notes_with_costs
        }

    def semantic_search(self, telegram_user_id, query_embedding, limit=5):
        """
        Wyszukiwanie semantyczne notatek używając cosine similarity

        Args:
            telegram_user_id: ID użytkownika
            query_embedding: Embedding zapytania (list)
            limit: Maksymalna liczba wyników

        Returns:
            Lista tuple (notatka, similarity_score) posortowana malejąco po score
        """
        # Pobierz wszystkie notatki użytkownika z embeddingami
        notatki = self.session.query(Notatka)\
            .filter(
                Notatka.telegram_user_id == telegram_user_id,
                Notatka.embedding.isnot(None)
            ).all()

        if not notatki:
            return []

        # Oblicz cosine similarity dla każdej notatki
        results = []
        query_vec = np.array(query_embedding)

        for notatka in notatki:
            try:
                # Deserializuj embedding z JSON
                note_embedding = json.loads(notatka.embedding)
                note_vec = np.array(note_embedding)

                # Cosine similarity
                similarity = np.dot(query_vec, note_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(note_vec)
                )

                # Konwertuj na procenty (0-100)
                similarity_percent = float(similarity * 100)

                results.append((notatka, similarity_percent))

            except (json.JSONDecodeError, ValueError) as e:
                # Pomiń notatki z uszkodzonymi embeddingami
                continue

        # Sortuj malejąco po similarity
        results.sort(key=lambda x: x[1], reverse=True)

        # Zwróć top N wyników
        return results[:limit]

    def close(self):
        """Zamyka połączenie z bazą"""
        self.session.close()
