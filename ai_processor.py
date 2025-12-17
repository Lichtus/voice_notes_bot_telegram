"""
Moduł przetwarzania audio i ekstrakcji struktury przez OpenAI
"""
import json
import logging
from io import BytesIO
from openai import OpenAI
from config import OPENAI_API_KEY, WHISPER_MODEL, GPT_MODEL, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


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
            str: Transkrypcja tekstu
        """
        try:
            audio_file = BytesIO(audio_bytes)
            audio_file.name = filename

            logger.info(f"Rozpoczynam transkrypcję audio ({len(audio_bytes)} bajtów)")

            transcript = self.client.audio.transcriptions.create(
                file=audio_file,
                model=WHISPER_MODEL,
                response_format="text"
            )

            logger.info(f"Transkrypcja zakończona: {len(transcript)} znaków")
            return transcript

        except Exception as e:
            logger.error(f"Błąd podczas transkrypcji: {e}")
            raise

    def extract_structure(self, transcription):
        """
        Wyciąga strukturę (temat, opis, zadania) z transkrypcji używając GPT-4o-mini

        Args:
            transcription: Tekst transkrypcji

        Returns:
            dict: {
                "temat": str,
                "opis": str,
                "zadania": list[str]
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

            # Parsowanie JSON
            result = json.loads(result_text)

            # Walidacja struktury
            if not all(key in result for key in ["temat", "opis", "zadania"]):
                raise ValueError("Nieprawidłowa struktura odpowiedzi z GPT")

            # Upewnij się że zadania to lista
            if not isinstance(result["zadania"], list):
                result["zadania"] = []

            logger.info(f"Ekstrakcja zakończona: temat='{result['temat']}', {len(result['zadania'])} zadań")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Błąd parsowania JSON z GPT: {e}")
            # Fallback - zwróć podstawową strukturę
            return {
                "temat": transcription[:100] if len(transcription) > 100 else transcription,
                "opis": transcription,
                "zadania": []
            }
        except Exception as e:
            logger.error(f"Błąd podczas ekstrakcji struktury: {e}")
            raise

    def process_voice_note(self, audio_bytes, filename="voice.ogg"):
        """
        Pełne przetwarzanie notatki głosowej: transkrypcja + ekstrakcja struktury

        Args:
            audio_bytes: Bajty pliku audio
            filename: Nazwa pliku

        Returns:
            dict: {
                "transkrypcja": str,
                "temat": str,
                "opis": str,
                "zadania": list[str]
            }
        """
        try:
            # Krok 1: Transkrypcja
            transcription = self.transcribe_audio(audio_bytes, filename)

            # Krok 2: Ekstrakcja struktury
            structure = self.extract_structure(transcription)

            # Połącz wyniki
            return {
                "transkrypcja": transcription,
                "temat": structure["temat"],
                "opis": structure["opis"],
                "zadania": structure["zadania"]
            }

        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania notatki głosowej: {e}")
            raise
