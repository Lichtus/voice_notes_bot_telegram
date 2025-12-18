"""
Moduł obsługi bazy danych SQLite dla Voice Notes Bot
"""
import json
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import DATABASE_PATH

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
    embedding = Column(Text)  # JSON embedding dla semantic search

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
    """Klasa zarządzająca bazą danych"""

    def __init__(self, db_path=DATABASE_PATH):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_notatka(self, telegram_user_id, temat, opis, transkrypcja, audio_file_id, zadania_list=None, embedding_vector=None):
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

        Returns:
            Notatka: Utworzona notatka
        """
        # Serializuj embedding do JSON jeśli podany
        embedding_json = None
        if embedding_vector:
            embedding_json = json.dumps(embedding_vector)

        notatka = Notatka(
            telegram_user_id=telegram_user_id,
            temat=temat,
            opis=opis,
            transkrypcja=transkrypcja,
            audio_file_id=audio_file_id,
            embedding=embedding_json
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

        return {
            "notatki": liczba_notatek,
            "zadania_wszystkie": liczba_zadan,
            "zadania_wykonane": liczba_wykonanych,
            "zadania_do_zrobienia": liczba_zadan - liczba_wykonanych
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
