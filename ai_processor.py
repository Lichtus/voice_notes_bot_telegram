"""
Moduł przetwarzania audio i ekstrakcji struktury przez OpenAI
"""
import json
import requests
import time
import logging
from io import BytesIO
from openai import OpenAI
from config import (OPENAI_API_KEY, TRANSCRIPTION_PROVIDER, TRANSCRIPTION_MODEL,
                    WHISPER_MODEL, GPT_MODEL, ASSEMBLYAI_API_KEY,
                    ASSEMBLYAI_LANGUAGE, EXTRACTION_PROMPT, DEEP_ANALYSIS_PROMPT)

logger = logging.getLogger(__name__)

# Model dla embeddingów
EMBEDDING_MODEL = "text-embedding-3-small"

ASSEMBLYAI_API = "https://api.assemblyai.com/v2"
ASSEMBLYAI_TIMEOUT_S = 600


class AIProcessor:
    """Klasa do przetwarzania audio i ekstrakcji danych przez AI"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def transcribe_audio(self, audio_bytes, filename="voice.ogg", liczba_mowcow=None):
        """
        Transkrybuje audio z rozpoznaniem mówców.

        Args:
            audio_bytes: Bajty pliku audio
            filename: Nazwa pliku — MUSI mieć rozszerzenie zgodne z rzeczywistą
                zawartością, API odrzuca niepasujące (np. plik M4A nazwany .ogg)
            liczba_mowcow: Dokładna liczba osób w nagraniu. Przy krótkich
                nagraniach grupowanie samo jej nie odgadnie i potrafi skleić
                dwie osoby w jedną. Obsługiwane tylko przez AssemblyAI —
                API przyjmuje dokładną liczbę, nie zakres.

        Returns:
            dict: {
                "tekst": str,          pełna transkrypcja
                "czas_s": int,         RZECZYWISTY czas nagrania z API
                "segmenty": list,      [{"mowca","start","end","tekst"}], puste dla whisper-1
                "mowcy": list[str],    posortowane etykiety mówców, np. ["A","B"]
                "tokeny_input": int,
                "tokeny_output": int,
            }
        """
        logger.info(
            f"Transkrypcja: {len(audio_bytes)} bajtów, dostawca {TRANSCRIPTION_PROVIDER}"
        )

        if TRANSCRIPTION_PROVIDER == "assemblyai":
            try:
                return self._transkrypcja_assemblyai(audio_bytes, liczba_mowcow)
            except Exception as e:
                # Awaria zewnętrznego dostawcy nie może kosztować użytkownika notatki
                logger.warning(f"AssemblyAI zawiódł ({e}); przechodzę na OpenAI")

        if liczba_mowcow:
            logger.info("OpenAI nie przyjmuje podpowiedzi o liczbie mówców — pomijam")
        return self._transkrypcja_openai(audio_bytes, filename)

    def _transkrypcja_assemblyai(self, audio_bytes, liczba_mowcow=None):
        """
        Diaryzacja z globalnym grupowaniem mówców — etykiety są spójne przez
        całe nagranie i nie wymagają żadnych próbek głosu.
        """
        if not ASSEMBLYAI_API_KEY:
            raise RuntimeError("brak ASSEMBLYAI_API_KEY")

        naglowki = {"authorization": ASSEMBLYAI_API_KEY}

        wgrane = requests.post(f"{ASSEMBLYAI_API}/upload", headers=naglowki,
                               data=audio_bytes, timeout=180)
        wgrane.raise_for_status()

        zadanie = {"audio_url": wgrane.json()["upload_url"],
                   "speaker_labels": True,
                   "language_code": ASSEMBLYAI_LANGUAGE}
        if liczba_mowcow:
            zadanie["speakers_expected"] = liczba_mowcow

        zlecenie = requests.post(f"{ASSEMBLYAI_API}/transcript", headers=naglowki,
                                 timeout=30, json=zadanie)
        zlecenie.raise_for_status()
        tid = zlecenie.json()["id"]

        koniec = time.time() + ASSEMBLYAI_TIMEOUT_S
        while True:
            if time.time() > koniec:
                raise TimeoutError(f"brak wyniku po {ASSEMBLYAI_TIMEOUT_S}s")
            stan = requests.get(f"{ASSEMBLYAI_API}/transcript/{tid}",
                                headers=naglowki, timeout=30).json()
            if stan["status"] == "completed":
                break
            if stan["status"] == "error":
                raise RuntimeError(stan.get("error", "nieznany błąd"))
            time.sleep(3)

        # Gdy diaryzacja nie zadziała dla języka, utterances bywa puste —
        # wtedy zostaje sam tekst, bez podziału na mówców.
        segmenty = [
            {
                "mowca": u["speaker"],
                "start": round(u["start"] / 1000, 2),
                "end": round(u["end"] / 1000, 2),
                "tekst": u["text"].strip(),
            }
            for u in (stan.get("utterances") or [])
        ]
        mowcy = sorted({s["mowca"] for s in segmenty})
        czas = int(round(stan.get("audio_duration") or 0)) or 1

        podpowiedz = f", podpowiedź: {liczba_mowcow} os." if liczba_mowcow else ""
        logger.info(f"AssemblyAI: {czas}s, {len(segmenty)} wypowiedzi, "
                    f"mówcy: {mowcy or 'brak'}, pewność: {stan.get('confidence')}{podpowiedz}")

        return {
            "tekst": stan.get("text") or "",
            "czas_s": czas,
            "segmenty": segmenty,
            "mowcy": mowcy,
            "tokeny_input": 0,      # rozliczenie za czas, nie za tokeny
            "tokeny_output": 0,
            "dostawca": "assemblyai",
        }

    def _transkrypcja_openai(self, audio_bytes, filename):
        """Diaryzacja OpenAI — grupuje mówców w obrębie fragmentu."""
        audio_file = BytesIO(audio_bytes)
        audio_file.name = filename

        try:
            odp = self.client.audio.transcriptions.create(
                file=audio_file,
                model=TRANSCRIPTION_MODEL,
                response_format="diarized_json",
                # WYMAGANE przez modele diaryzujące dla nagrań dłuższych niż
                # 30 sekund — bez tego API zwraca 400. "auto" normalizuje
                # głośność i tnie nagranie po wykryciu aktywności głosowej.
                chunking_strategy="auto",
            )
        except Exception as e:
            # Nie zostawiamy użytkownika bez notatki, jeśli model diaryzujący
            # zawiedzie — Whisper nie da mówców, ale da treść.
            logger.warning(f"Model diaryzujący zawiódł ({e}); używam {WHISPER_MODEL}")
            return self._transkrypcja_awaryjna(audio_bytes, filename)

        segmenty = [
            {
                "mowca": s.speaker,
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "tekst": s.text.strip(),
            }
            for s in (odp.segments or [])
        ]
        mowcy = sorted({s["mowca"] for s in segmenty})

        uzycie = getattr(odp, "usage", None)
        tok_in = getattr(uzycie, "input_tokens", 0) or 0
        tok_out = getattr(uzycie, "output_tokens", 0) or 0

        czas = int(round(odp.duration or 0)) or 1
        logger.info(
            f"Transkrypcja: {len(odp.text)} znaków, {czas}s, "
            f"{len(segmenty)} segmentów, mówcy: {mowcy or 'brak'}"
        )

        return {
            "tekst": odp.text,
            "czas_s": czas,
            "segmenty": segmenty,
            "mowcy": mowcy,
            "tokeny_input": tok_in,
            "tokeny_output": tok_out,
            "dostawca": "openai",
        }

    def _transkrypcja_awaryjna(self, audio_bytes, filename):
        """Whisper bez diaryzacji. Czasu nagrania nie zna, więc go szacuje."""
        audio_file = BytesIO(audio_bytes)
        audio_file.name = filename
        tekst = self.client.audio.transcriptions.create(
            file=audio_file, model=WHISPER_MODEL, response_format="text"
        )
        return {
            "tekst": tekst,
            "czas_s": max(1, int(len(audio_bytes) / 10000)),
            "segmenty": [],
            "mowcy": [],
            "tokeny_input": 0,
            "tokeny_output": 0,
            "dostawca": "whisper",
        }

    def extract_structure(self, transcription):
        """
        Wyciąga strukturę (temat, opis, zadania) z transkrypcji używając GPT-4o-mini

        Args:
            transcription: Tekst transkrypcji

        Returns:
            tuple: (result_dict, usage_dict)
                - result_dict: {
                    "temat": str,
                    "opis": str,
                    "zadania": list[str]
                }
                - usage_dict: {
                    "input_tokens": int,
                    "output_tokens": int,
                    "total_tokens": int
                }
        """
        try:
            logger.info(f"Ekstrakcja struktury z transkrypcji ({len(transcription)} znaków)")

            prompt = EXTRACTION_PROMPT.format(transcription=transcription)

            response = self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Jesteś asystentem analizującym notatki głosowe. Zwracasz tylko JSON bez dodatkowych komentarzy."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            logger.info(f"Otrzymano odpowiedź z GPT: {result_text}")

            # Pobierz informacje o usage
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            logger.info(f"GPT usage: {usage['input_tokens']} input + {usage['output_tokens']} output = {usage['total_tokens']} total")

            # Parsowanie JSON
            result = json.loads(result_text)

            # Walidacja struktury
            required_keys = ["temat", "opis", "zadania", "kategoria"]
            if not all(key in result for key in required_keys):
                raise ValueError("Nieprawidłowa struktura odpowiedzi z GPT")

            # Upewnij się że zadania to lista
            if not isinstance(result["zadania"], list):
                result["zadania"] = []

            # Walidacja kategorii
            allowed_categories = ["Praca", "Dom", "Inne"]
            if result["kategoria"] not in allowed_categories:
                logger.warning(f"Nieprawidłowa kategoria '{result['kategoria']}', ustawiam 'Inne'")
                result["kategoria"] = "Inne"

            # Walidacja confidence (opcjonalne)
            if "confidence" not in result:
                result["confidence"] = 0.5  # Domyślna wartość jeśli GPT nie zwrócił
            else:
                try:
                    confidence = float(result["confidence"])
                    # Upewnij się że jest w zakresie 0-1
                    result["confidence"] = max(0.0, min(1.0, confidence))
                except (ValueError, TypeError):
                    logger.warning(f"Nieprawidłowa wartość confidence: {result['confidence']}, ustawiam 0.5")
                    result["confidence"] = 0.5

            logger.info(f"Ekstrakcja zakończona: temat='{result['temat']}', kategoria='{result['kategoria']}' (confidence: {result['confidence']:.2f}), {len(result['zadania'])} zadań")
            return result, usage

        except json.JSONDecodeError as e:
            logger.error(f"Błąd parsowania JSON z GPT: {e}")
            # Fallback - zwróć podstawową strukturę bez usage
            return {
                "temat": transcription[:100] if len(transcription) > 100 else transcription,
                "opis": transcription,
                "zadania": [],
                "kategoria": "Inne",
                "confidence": 0.0  # Brak confidence w przypadku błędu
            }, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        except Exception as e:
            logger.error(f"Błąd podczas ekstrakcji struktury: {e}")
            raise

    def get_embedding(self, text):
        """
        Generuje embedding dla tekstu używając OpenAI

        Args:
            text: Tekst do embedowania

        Returns:
            tuple: (embedding_vector, usage_tokens)
                - embedding_vector: Wektor embedding (list)
                - usage_tokens: Liczba użytych tokenów (int)
        """
        try:
            logger.info(f"Generowanie embedding dla tekstu ({len(text)} znaków)")

            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )

            embedding = response.data[0].embedding
            usage_tokens = response.usage.total_tokens

            logger.info(f"Embedding wygenerowany: {len(embedding)} wymiarów, {usage_tokens} tokenów")

            return embedding, usage_tokens

        except Exception as e:
            logger.error(f"Błąd podczas generowania embedding: {e}")
            raise

    def process_voice_note(self, audio_bytes, filename="voice.ogg"):
        """
        Pełne przetwarzanie notatki głosowej: transkrypcja + ekstrakcja struktury + koszty

        Args:
            audio_bytes: Bajty pliku audio
            filename: Nazwa pliku

        Returns:
            dict: {
                "transkrypcja": str,
                "temat": str,
                "opis": str,
                "zadania": list[str],
                "kategoria": str,
                "embedding": list (wektor),
                "cost_data": {
                    "audio_duration_seconds": int,
                    "tokens_input": int,
                    "tokens_output": int,
                    "tokens_embedding": int,
                    "cost_whisper_usd": float,
                    "cost_gpt_input_usd": float,
                    "cost_gpt_output_usd": float,
                    "cost_embedding_usd": float,
                    "cost_total_usd": float,
                    "processing_time": float,
                    "auto_category_confidence": float
                }
            }
        """
        import time
        start_time = time.time()

        try:
            from cost_calculator import CostCalculator

            # Krok 1: Transkrypcja (z rozpoznaniem mówców)
            tr = self.transcribe_audio(audio_bytes, filename)
            transcription = tr["tekst"]
            audio_duration = tr["czas_s"]

            # Krok 2: Ekstrakcja struktury (ze smart klasyfikacją)
            structure, gpt_usage = self.extract_structure(transcription)

            # Krok 3: Generowanie embedding dla semantycznego wyszukiwania
            # Używamy kombinacji tematu i opisu dla najlepszego dopasowania
            embedding_text = f"{structure['temat']}. {structure['opis']}"
            embedding, embedding_tokens = self.get_embedding(embedding_text)

            # Krok 4: Obliczanie kosztów
            cost_whisper = CostCalculator.calculate_transcription_cost(
                audio_duration, tr.get("dostawca") or TRANSCRIPTION_MODEL)
            cost_gpt_in, cost_gpt_out, cost_gpt_total = CostCalculator.calculate_gpt_cost(
                gpt_usage['input_tokens'],
                gpt_usage['output_tokens']
            )
            cost_embedding = CostCalculator.calculate_embedding_cost(embedding_tokens)
            cost_total = CostCalculator.calculate_total_cost(
                cost_whisper,
                cost_gpt_in,
                cost_gpt_out,
                cost_embedding
            )

            # Oblicz czas procesowania
            processing_time = time.time() - start_time
            logger.info(f"Przetwarzanie zakończone w {processing_time:.2f}s")

            # Połącz wyniki
            return {
                "transkrypcja": transcription,
                "segmenty": tr["segmenty"],
                "mowcy": tr["mowcy"],
                "temat": structure["temat"],
                "opis": structure["opis"],
                "zadania": structure["zadania"],
                "kategoria": structure["kategoria"],
                "embedding": embedding,
                "cost_data": {
                    "audio_duration_seconds": audio_duration,
                    "tokens_input": gpt_usage['input_tokens'],
                    "tokens_output": gpt_usage['output_tokens'],
                    "tokens_embedding": embedding_tokens,
                    "cost_whisper_usd": cost_whisper,
                    "cost_gpt_input_usd": cost_gpt_in,
                    "cost_gpt_output_usd": cost_gpt_out,
                    "cost_embedding_usd": cost_embedding,
                    "cost_total_usd": cost_total,
                    "processing_time": processing_time,
                    "auto_category_confidence": structure.get("confidence", 0.5)
                }
            }

        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania notatki głosowej: {e}")
            raise

    def analyze_long_note(self, transcription):
        """
        Dogłębna analiza długiej notatki z uczestnikami, sekcjami, cytatami i chronologią

        Args:
            transcription: Pełna transkrypcja notatki

        Returns:
            tuple: (analysis_dict, usage_dict)
                - analysis_dict: {
                    "tytul": str,
                    "uczestnicy": list[str],
                    "sekcje": list[dict],
                    "ustalenia": list[str],
                    "daty_chronologicznie": list[dict],
                    "kluczowe_daty_podsumowanie": str
                }
                - usage_dict: {
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                }
        """
        try:
            logger.info(f"Rozpoczynam dogłębną analizę notatki ({len(transcription)} znaków)")

            prompt = DEEP_ANALYSIS_PROMPT.format(transcription=transcription)

            response = self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "Jesteś profesjonalnym analitykiem i dokumentatorem."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            content = response.choices[0].message.content
            usage = response.usage

            result = json.loads(content)

            # Walidacja struktury
            required_keys = ['tytul', 'uczestnicy', 'sekcje', 'ustalenia', 'daty_chronologicznie', 'kluczowe_daty_podsumowanie']
            for key in required_keys:
                if key not in result:
                    if key in ['uczestnicy', 'ustalenia', 'daty_chronologicznie']:
                        result[key] = []
                    else:
                        result[key] = ""

            # Upewnij się że uczestnicy to lista
            if not isinstance(result.get("uczestnicy"), list):
                result["uczestnicy"] = []

            # Upewnij się że sekcje to lista
            if not isinstance(result.get("sekcje"), list):
                result["sekcje"] = []

            # Upewnij się że ustalenia to lista
            if not isinstance(result.get("ustalenia"), list):
                result["ustalenia"] = []

            # Upewnij się że daty_chronologicznie to lista
            if not isinstance(result.get("daty_chronologicznie"), list):
                result["daty_chronologicznie"] = []

            usage_dict = {
                'prompt_tokens': usage.prompt_tokens,
                'completion_tokens': usage.completion_tokens,
                'total_tokens': usage.total_tokens
            }

            logger.info(f"Analiza zakończona: {len(result.get('sekcje', []))} sekcji, {len(result.get('uczestnicy', []))} uczestników, {usage_dict['total_tokens']} tokenów")

            return result, usage_dict

        except json.JSONDecodeError as e:
            logger.error(f"Błąd parsowania JSON z analizy: {e}")
            # Fallback - zwróć pustą strukturę
            return {
                "tytul": "",
                "uczestnicy": [],
                "sekcje": [],
                "ustalenia": [],
                "daty_chronologicznie": [],
                "kluczowe_daty_podsumowanie": ""
            }, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        except Exception as e:
            logger.error(f"Błąd podczas analizy głębokiej: {e}")
            raise
