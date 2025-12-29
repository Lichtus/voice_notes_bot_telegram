-- Migracja: Dodaje kolumny 'kategoria' i 'deleted_at' do tabeli notatki
--
-- Uruchom: sqlite3 voice_notes.db < migrate.sql

-- Dodaj kolumnę kategoria (jeśli nie istnieje)
ALTER TABLE notatki ADD COLUMN kategoria VARCHAR(50) DEFAULT 'Inne' NOT NULL;

-- Dodaj kolumnę deleted_at (jeśli nie istnieje)
ALTER TABLE notatki ADD COLUMN deleted_at TIMESTAMP NULL;

-- Wyświetl potwierdzenie
SELECT '✅ Migracja zakończona pomyślnie!' as status;
SELECT 'Dodano kolumny: kategoria, deleted_at' as info;
