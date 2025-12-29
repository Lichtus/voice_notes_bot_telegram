"""
Moduł przetwarzania audio i ekstrakcji struktury przez OpenAI
"""
import json
import logging
from io import BytesIO
from openai import OpenAI
from config import OPENAI_API_KEY, WHISPER_MODEL, GPT_MODEL, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

# Model dla embeddingów
EMBEDDING_MODEL = "text-embedding-3-small"


class AIProcessor:
    """Klasa do przetwarzania audio i ekstrakcji danych przez AI"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def transcribe_audio(self, audio_bytes, filename="voice.ogg"):
        """
        Transkrybuje audio do tekstu używając Whisper

        Args:
            audio_bytes: Bajty pliku audio
            filename: Nazwa pliku (dla OpenAI API)

        Returns:
            tuple: (transcript_text, duration_seconds)
                - transcript_text: Transkrypcja tekstu
                - duration_seconds: Szacowana długość audio w sekundach
        """
        try:
            audio_file = BytesIO(audio_bytes)
            audio_file.name = filename

            logger.info(f"Rozpoczynam transkrypcję audio ({len(audio_bytes)} bajtów)")

            # Szacowanie długości audio na podstawie rozmiaru pliku
            # Dla OGG Opus: ~6-12 KB/s (zależne od jakości)
            # Używamy konserwatywnego szacunku: 10 KB/s
            estimated_duration = max(1, len(audio_bytes) / 10000)  # w sekundach

            transcript = self.client.audio.transcriptions.create(
                file=audio_file,
                model=WHISPER_MODEL,
                response_format="text"
            )

            logger.info(f"Transkrypcja zakończona: {len(transcript)} znaków, ~{estimated_duration:.1f}s")
            return transcript, int(estimated_duration)

        except Exception as e:
            logger.error(f"Błąd podczas transkrypcji: {e}")
            raise

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

            # Krok 1: Transkrypcja
            transcription, audio_duration = self.transcribe_audio(audio_bytes, filename)

            # Krok 2: Ekstrakcja struktury (ze smart klasyfikacją)
            structure, gpt_usage = self.extract_structure(transcription)

            # Krok 3: Generowanie embedding dla semantycznego wyszukiwania
            # Używamy kombinacji tematu i opisu dla najlepszego dopasowania
            embedding_text = f"{structure['temat']}. {structure['opis']}"
            embedding, embedding_tokens = self.get_embedding(embedding_text)

            # Krok 4: Obliczanie kosztów
            cost_whisper = CostCalculator.calculate_whisper_cost(audio_duration)
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
