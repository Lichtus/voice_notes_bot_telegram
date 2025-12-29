"""
Telegram Bot do notatek głosowych z automatyczną ekstrakcją struktury przez AI
"""
import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, validate_config
from database import Database
from ai_processor import AIProcessor

# Konfiguracja loggera
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Stany konwersacji
COLLECTING_AUDIO, WAITING_CONFIRMATION, EDITING_TEMAT, EDITING_OPIS, WAITING_PHOTOS, ASKING_PDF, EDITING_NOTE = range(7)

# Globalne instancje
db = Database()
ai = AIProcessor()

# Tymczasowe dane notatki (w sesji użytkownika)
pending_notes = {}

# Przechowuje ID notatki podczas edycji
editing_note_id = {}


def check_user_allowed(func):
    """Dekorator sprawdzający czy użytkownik ma dostęp"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USER_IDS:
            logger.warning(f"Nieautoryzowany dostęp: user_id={user_id}")
            await update.message.reply_text(
                "❌ Nie masz dostępu do tego bota.\n"
                f"Twój User ID: {user_id}"
            )
            return
        return await func(update, context)
    return wrapper


async def handle_webapp_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler logowania do aplikacji webowej"""
    import random
    import requests

    user = update.effective_user
    user_id = user.id

    # Generuj 6-cyfrowy kod
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    # Wyślij kod do użytkownika
    await update.message.reply_text(
        f"🔐 *Kod weryfikacyjny do logowania w aplikacji webowej:*\n\n"
        f"`{code}`\n\n"
        f"*Twój Telegram User ID:*\n`{user_id}`\n\n"
        f"📱 Wpisz te dane na stronie logowania.\n"
        f"⏱️ Kod ważny przez 5 minut.",
        parse_mode='Markdown'
    )

    # Wyślij kod do web_app przez API
    try:
        # Pobierz URL aplikacji webowej (zakładamy localhost:5000, można to zmienić w .env)
        web_app_url = os.getenv('WEB_APP_URL', 'http://localhost:5000')

        response = requests.post(
            f"{web_app_url}/api/store-code",
            json={
                'user_id': user_id,
                'code': code,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username
            },
            timeout=5
        )

        if response.status_code == 200:
            logger.info(f"Login code sent to web app for user {user_id}")
        else:
            logger.error(f"Failed to send code to web app: {response.status_code}")

    except Exception as e:
        logger.error(f"Error sending code to web app: {e}")
        # Nie pokazuj błędu użytkownikowi - kod i tak dostał


@check_user_allowed
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /start"""
    # Sprawdź czy jest parametr webapp_login
    if context.args and len(context.args) > 0 and context.args[0] == 'webapp_login':
        await handle_webapp_login(update, context)
        return

    await update.message.reply_text(
        "🎙️ *Witaj w Voice Notes Bot!*\n\n"
        "📝 *Dodawanie notatek:*\n"
        "• Wyślij *voice message* (max 15-20 min)\n"
        "• Lub wgraj *plik audio* (MP3, WAV, M4A, OGG)\n"
        "• Bot automatycznie wyciągnie temat, opis i zadania!\n\n"
        "🔍 *Głosowe wyszukiwanie:*\n"
        "• Powiedz: *\"Szukaj [temat]\"* w voice message\n"
        "• Np: \"Szukaj spotkanie z Jankiem\"\n"
        "• Działa też: znajdź, wyszukaj, pokaż, search, find\n"
        "• Otrzymasz wyniki z % dopasowania\n\n"
        "📱 *Komendy:*\n"
        "• `/lista` - ostatnie notatki\n"
        "• `/notatka [id]` - odsłuchaj pełną notatkę\n"
        "• `/ostatnia` - ostatnia notatka\n"
        "• `/szukaj [tekst]` - szukaj tekstowo\n"
        "• `/zadania` - zadania do zrobienia\n"
        "• `/wykonane [id]` - oznacz zadanie\n"
        "• `/stats` - statystyki\n\n"
        "⚠️ *Limit:* max 20 minut nagrania",
        parse_mode='Markdown'
    )


@check_user_allowed
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler notatek głosowych, plików audio i głosowego wyszukiwania"""
    user_id = update.effective_user.id

    # Pobierz plik audio (voice message lub audio file)
    if update.message.voice:
        audio_obj = update.message.voice
        file_type = "voice"
        filename = "voice.ogg"
    elif update.message.audio:
        audio_obj = update.message.audio
        file_type = "audio"
        # Użyj oryginalnej nazwy pliku lub domyślnej z rozszerzeniem
        filename = update.message.audio.file_name or f"audio.{update.message.audio.mime_type.split('/')[-1]}"
    else:
        await update.message.reply_text("❌ Błąd: Brak pliku audio")
        return ConversationHandler.END

    await update.message.reply_text("🎤 Plik audio otrzymany! Przetwarzam...")

    try:
        # Pobierz plik
        file = await context.bot.get_file(audio_obj.file_id)
        audio_bytes = await file.download_as_bytearray()

        # Transkrypcja dla wykrycia keywordu (szybka, bez embeddingu)
        await update.message.reply_text("🔄 Transkrybuję audio...")
        transcription, _ = ai.transcribe_audio(bytes(audio_bytes), filename=filename)

        # Loguj transkrypcję dla debugowania
        logger.info(f"Transkrypcja otrzymana: '{transcription}'")

        # Wykryj keywordy wyszukiwania
        search_keywords = ["szukaj", "znajdź", "wyszukaj", "pokaż", "search", "find", "znajdz"]

        # Wyczyść transkrypcję - usuń znaki interpunkcyjne z początku
        transcription_clean = transcription.strip().lstrip(".,!?;: ")
        transcription_lower = transcription_clean.lower()

        # Pobierz pierwsze słowo
        first_word = transcription_lower.split()[0] if transcription_lower.split() else ""

        # Sprawdź czy pierwsze słowo to keyword
        is_search = False
        search_query = None

        for keyword in search_keywords:
            if first_word == keyword or transcription_lower.startswith(keyword + " "):
                # Usuń pierwsze słowo (keyword) z transkrypcji
                words = transcription_clean.split(maxsplit=1)
                search_query = words[1] if len(words) > 1 else ""
                is_search = True
                logger.info(f"✓ Wykryto keyword '{keyword}' -> wyszukiwanie: '{search_query}'")
                break

        # Jeśli to wyszukiwanie - obsłuż przez handle_voice_search
        if is_search and search_query:
            await handle_voice_search(update, context, search_query)
            return ConversationHandler.END

        logger.info(f"Pierwsze słowo: '{first_word}' - nie wykryto keywordu wyszukiwania, tworzę notatkę")

        # Zapisz audio do kolekcji (możliwe wieloczęściowe nagrania)
        if user_id not in pending_notes:
            pending_notes[user_id] = {
                "audio_parts": [],  # Lista (audio_bytes, filename, file_id)
                "photos": []
            }

        # Dodaj część audio
        pending_notes[user_id]["audio_parts"].append({
            "bytes": bytes(audio_bytes),
            "filename": filename,
            "file_id": audio_obj.file_id
        })

        # Zapytaj czy dodać więcej
        part_count = len(pending_notes[user_id]["audio_parts"])
        keyboard = [
            [InlineKeyboardButton("✅ To wszystko - przetwórz", callback_data="finalize_audio")],
            [InlineKeyboardButton("➕ Dodaj więcej nagrań", callback_data="more_audio")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🎤 *Nagrane części: {part_count}*\n\n"
            f"Czy to cała notatka, czy chcesz dodać więcej nagrań?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        return COLLECTING_AUDIO

    except Exception as e:
        logger.error(f"Błąd przetwarzania audio: {e}")
        await update.message.reply_text(
            f"❌ Wystąpił błąd podczas przetwarzania:\n`{str(e)}`",
            parse_mode='Markdown'
        )
        return ConversationHandler.END


async def handle_voice_search(update: Update, context: ContextTypes.DEFAULT_TYPE, search_query: str):
    """Handler głosowego wyszukiwania notatek"""
    user_id = update.effective_user.id

    try:
        await update.message.reply_text(f"🔍 Szukam notatek dla: *\"{search_query}\"*", parse_mode='Markdown')

        # Generuj embedding dla query (get_embedding zwraca tuple: (embedding, tokens))
        query_embedding, _ = ai.get_embedding(search_query)

        # Wyszukiwanie semantyczne
        results = db.semantic_search(user_id, query_embedding, limit=5)

        if not results:
            await update.message.reply_text(
                "😕 Nie znaleziono żadnych notatek.\n\n"
                "Spróbuj:\n"
                "• Użyć innych słów\n"
                "• Bardziej ogólnego zapytania"
            )
            return

        # Wyślij każdy wynik osobno z przyciskiem
        await update.message.reply_text(
            f"🔍 *Wyniki wyszukiwania dla:* \"{search_query}\"\n"
            f"Znaleziono {len(results)} notatek\n",
            parse_mode='Markdown'
        )

        for notatka, similarity in results:
            # Zaokrąglij procent do 1 miejsca po przecinku
            percent = round(similarity, 1)
            data_str = notatka.data_utworzenia.strftime("%Y-%m-%d %H:%M")

            # Ikona w zależności od dopasowania
            if percent >= 80:
                icon = "🟢"
            elif percent >= 60:
                icon = "🟡"
            else:
                icon = "🟠"

            zadania_count = len(notatka.zadania)
            zadania_info = f" • {zadania_count} zadań" if zadania_count > 0 else ""

            # Przycisk do odsłuchania
            keyboard = [[InlineKeyboardButton("🎧 Odsłuchaj notatkę", callback_data=f"play_{notatka.id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = (
                f"{icon} *{percent}%* dopasowania\n"
                f"🆔 Notatka #{notatka.id}\n"
                f"📅 {data_str}{zadania_info}\n"
                f"📌 *{notatka.temat}*\n"
                f"📝 {notatka.opis[:150]}{'...' if len(notatka.opis) > 150 else ''}"
            )

            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Błąd podczas głosowego wyszukiwania: {e}")
        await update.message.reply_text(
            f"❌ Wystąpił błąd podczas wyszukiwania:\n`{str(e)}`",
            parse_mode='Markdown'
        )


async def show_note_preview(update: Update, user_id: int):
    """Pokazuje podgląd notatki do zatwierdzenia"""
    note = pending_notes.get(user_id)
    if not note:
        return

    zadania_text = ""
    if note["zadania"]:
        zadania_text = "\n📋 *ZADANIA:*\n"
        for i, zadanie in enumerate(note["zadania"], 1):
            zadania_text += f"{i}. {zadanie}\n"
    else:
        zadania_text = "\n📋 *ZADANIA:* brak"

    message = (
        "✅ *Notatka przetworzona!*\n\n"
        f"📌 *TEMAT:*\n{note['temat']}\n\n"
        f"📝 *OPIS:*\n{note['opis']}"
        f"{zadania_text}\n"
        "━━━━━━━━━━━━━━━━\n"
        "📸 Czy chcesz dodać zdjęcia do notatki?"
    )

    keyboard = [
        [
            InlineKeyboardButton("📸 Dodaj zdjęcia", callback_data="add_photos"),
            InlineKeyboardButton("⏭️ Pomiń", callback_data="skip_photos")
        ],
        [
            InlineKeyboardButton("✏️ Edytuj temat", callback_data="edit_temat"),
            InlineKeyboardButton("❌ Anuluj", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def ask_for_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prosi użytkownika o wysłanie zdjęć"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📸 *Dodawanie zdjęć do notatki*\n\n"
        "Wyślij jedno lub więcej zdjęć.\n"
        "Gdy skończysz, kliknij przycisk poniżej.\n\n"
        "💡 Możesz wysłać wiele zdjęć po kolei.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Zakończ dodawanie zdjęć", callback_data="finish_photos")
        ]])
    )

    return WAITING_PHOTOS


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler odbierania zdjęć"""
    user_id = update.effective_user.id

    if user_id not in pending_notes:
        await update.message.reply_text("❌ Błąd: Brak notatki w trakcie tworzenia.")
        return ConversationHandler.END

    # Pobierz największe zdjęcie (najlepsza jakość)
    photo = update.message.photo[-1]

    # Dodaj file_id do listy zdjęć
    pending_notes[user_id]["photos"].append(photo.file_id)

    photo_count = len(pending_notes[user_id]["photos"])
    await update.message.reply_text(
        f"✅ Zdjęcie dodane! ({photo_count} zdjęć)\n"
        "Wyślij kolejne lub kliknij 'Zakończ dodawanie zdjęć'."
    )

    return WAITING_PHOTOS


async def ask_for_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pyta użytkownika czy chce wygenerować PDF"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    note = pending_notes.get(user_id)

    if not note:
        await query.edit_message_text("❌ Błąd: Brak notatki")
        return ConversationHandler.END

    photo_count = len(note["photos"])
    photos_info = f"\n📸 Załączonych zdjęć: {photo_count}" if photo_count > 0 else ""

    message = (
        f"✅ *Notatka gotowa do zapisu!*{photos_info}\n\n"
        "🎨 Czy chcesz wygenerować sformatowany PDF z notatką?"
    )

    keyboard = [
        [
            InlineKeyboardButton("📄 Tak, generuj PDF", callback_data="generate_pdf"),
            InlineKeyboardButton("⏭️ Nie, zapisz bez PDF", callback_data="save_without_pdf")
        ]
    ]

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    return ASKING_PDF


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler przycisków inline"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    action = query.data

    if action == "finalize_audio":
        # Przetwórz wszystkie zebrane części audio
        if user_id not in pending_notes or not pending_notes[user_id]["audio_parts"]:
            await query.edit_message_text("❌ Błąd: Brak nagrań do przetworzenia")
            return ConversationHandler.END

        audio_parts = pending_notes[user_id]["audio_parts"]
        part_count = len(audio_parts)

        await query.edit_message_text(
            f"🔄 Przetwarzam {part_count} {'część' if part_count == 1 else 'części'} audio...",
            parse_mode='Markdown'
        )

        try:
            # Zbierz wszystkie transkrypcje
            transcriptions = []
            total_duration = 0

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔄 Transkrybuję wszystkie części..."
            )

            for i, part in enumerate(audio_parts, 1):
                logger.info(f"Transkrybuję część {i}/{part_count}")
                transcript, duration = ai.transcribe_audio(part["bytes"], filename=part["filename"])
                transcriptions.append(f"[Część {i}]\n{transcript}")
                total_duration += duration

            # Połącz transkrypcje
            combined_transcription = "\n\n".join(transcriptions)

            logger.info(f"Połączona transkrypcja: {len(combined_transcription)} znaków, {total_duration}s")

            # Ekstrakcja struktury z połączonej transkrypcji
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🤖 Analizuję i wyciągam strukturę..."
            )

            structure, gpt_usage = ai.extract_structure(combined_transcription)

            # Generowanie embedding
            embedding_text = f"{structure['temat']}. {structure['opis']}"
            embedding, embedding_tokens = ai.get_embedding(embedding_text)

            # Obliczanie kosztów
            from cost_calculator import CostCalculator

            cost_whisper = CostCalculator.calculate_whisper_cost(total_duration)
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

            # Zapisz wyniki w pending_notes (nadpisz strukturę)
            # Użyj pierwszego audio jako główne (do odsłuchania)
            pending_notes[user_id]["audio_file_id"] = audio_parts[0]["file_id"]
            pending_notes[user_id]["transkrypcja"] = combined_transcription
            pending_notes[user_id]["temat"] = structure["temat"]
            pending_notes[user_id]["opis"] = structure["opis"]
            pending_notes[user_id]["zadania"] = structure["zadania"]
            pending_notes[user_id]["embedding"] = embedding
            pending_notes[user_id]["cost_data"] = {
                "audio_duration_seconds": total_duration,
                "tokens_input": gpt_usage['input_tokens'],
                "tokens_output": gpt_usage['output_tokens'],
                "tokens_embedding": embedding_tokens,
                "cost_whisper_usd": cost_whisper,
                "cost_gpt_input_usd": cost_gpt_in,
                "cost_gpt_output_usd": cost_gpt_out,
                "cost_embedding_usd": cost_embedding,
                "cost_total_usd": cost_total
            }

            # Wyświetl koszt
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"💰 Koszt przetworzenia: {CostCalculator.format_cost_usd(cost_total)}",
                parse_mode='Markdown'
            )

            # Pokaż podgląd i przejdź do WAITING_CONFIRMATION
            # Musimy stworzyć "fake" update z message
            class FakeMessage:
                def __init__(self, chat_id):
                    self.chat_id = chat_id
                    self.chat = self
                    self.id = chat_id

                async def reply_text(self, text, **kwargs):
                    return await context.bot.send_message(
                        chat_id=self.chat_id,
                        text=text,
                        **kwargs
                    )

            fake_update = type('obj', (object,), {
                'message': FakeMessage(update.effective_chat.id),
                'effective_user': update.effective_user
            })()

            await show_note_preview(fake_update, user_id)

            return WAITING_CONFIRMATION

        except Exception as e:
            logger.error(f"Błąd przetwarzania wieloczęściowego audio: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Wystąpił błąd podczas przetwarzania:\n`{str(e)}`",
                parse_mode='Markdown'
            )

            # Wyczyść pending_notes
            if user_id in pending_notes:
                del pending_notes[user_id]

            return ConversationHandler.END

    elif action == "more_audio":
        # Poczekaj na więcej nagrań
        await query.edit_message_text(
            "🎤 *Czekam na kolejne nagranie...*\n\n"
            "Wyślij następną część audio lub plik audio.",
            parse_mode='Markdown'
        )
        return COLLECTING_AUDIO

    elif action == "add_photos":
        # Rozpocznij dodawanie zdjęć
        return await ask_for_photos(update, context)

    elif action == "skip_photos":
        # Pomiń zdjęcia i przejdź do pytania o PDF
        return await ask_for_pdf(update, context)

    elif action == "finish_photos":
        # Zakończ dodawanie zdjęć i przejdź do pytania o PDF
        return await ask_for_pdf(update, context)

    elif action == "generate_pdf":
        # Zapisz notatkę i generuj PDF
        note = pending_notes.get(user_id)
        if note:
            # Zapisz do bazy
            notatka = db.add_notatka(
                telegram_user_id=user_id,
                temat=note["temat"],
                opis=note["opis"],
                transkrypcja=note["transkrypcja"],
                audio_file_id=note["audio_file_id"],
                zadania_list=note["zadania"],
                embedding_vector=note.get("embedding"),
                photo_file_ids=note["photos"] if note["photos"] else None,
                cost_data=note.get("cost_data")  # Dane o kosztach API
            )

            await query.edit_message_text("📝 Zapisuję notatkę i generuję PDF...", parse_mode='Markdown')

            # Generuj PDF
            try:
                pdf_path = await generate_pdf(note, notatka.id, context)

                # Wyślij PDF
                with open(pdf_path, 'rb') as pdf_file:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=pdf_file,
                        filename=f"notatka_{notatka.id}.pdf",
                        caption=f"📄 *PDF Notatki #{notatka.id}*\n📌 {note['temat']}",
                        parse_mode='Markdown'
                    )

                # Usuń tymczasowy plik PDF
                import os
                os.remove(pdf_path)

                # Formatuj datę
                data_str = notatka.data_utworzenia.strftime("%d.%m.%Y %H:%M:%S")

                # Komunikat potwierdzający z pełnymi szczegółami
                message = (
                    f"🎉 *Notatka zapisana i PDF wygenerowany!*\n\n"
                    f"🆔 *Numer notatki:* #{notatka.id}\n"
                    f"📅 *Data utworzenia:* {data_str}"
                )

                # Przycisk do pobrania transkrypcji
                keyboard = [[
                    InlineKeyboardButton("📄 Pobierz transkrypcję (TXT)", callback_data=f"download_transcript_{notatka.id}")
                ]]

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

            except Exception as e:
                logger.error(f"Błąd generowania PDF: {e}")

                # Formatuj datę
                data_str = notatka.data_utworzenia.strftime("%d.%m.%Y %H:%M:%S")

                # Komunikat z błędem PDF ale notatkę zapisano
                message = (
                    f"✅ *Notatka zapisana!*\n"
                    f"❌ Błąd generowania PDF: {str(e)}\n\n"
                    f"🆔 *Numer notatki:* #{notatka.id}\n"
                    f"📅 *Data utworzenia:* {data_str}"
                )

                # Przycisk do pobrania transkrypcji
                keyboard = [[
                    InlineKeyboardButton("📄 Pobierz transkrypcję (TXT)", callback_data=f"download_transcript_{notatka.id}")
                ]]

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

            del pending_notes[user_id]

        return ConversationHandler.END

    elif action == "save_without_pdf":
        # Zapisz notatkę bez PDF
        note = pending_notes.get(user_id)
        if note:
            notatka = db.add_notatka(
                telegram_user_id=user_id,
                temat=note["temat"],
                opis=note["opis"],
                transkrypcja=note["transkrypcja"],
                audio_file_id=note["audio_file_id"],
                zadania_list=note["zadania"],
                embedding_vector=note.get("embedding"),
                photo_file_ids=note["photos"] if note["photos"] else None,
                cost_data=note.get("cost_data")  # Dane o kosztach API
            )
            del pending_notes[user_id]

            # Formatuj datę
            data_str = notatka.data_utworzenia.strftime("%d.%m.%Y %H:%M:%S")

            photo_count = len(note["photos"])
            photos_info = f" z {photo_count} zdjęciami" if photo_count > 0 else ""

            # Komunikat potwierdzający z pełnymi szczegółami
            message = (
                f"🎉 *Notatka zapisana{photos_info}!*\n\n"
                f"🆔 *Numer notatki:* #{notatka.id}\n"
                f"📅 *Data utworzenia:* {data_str}"
            )

            # Przycisk do pobrania transkrypcji
            keyboard = [[
                InlineKeyboardButton("📄 Pobierz transkrypcję (TXT)", callback_data=f"download_transcript_{notatka.id}")
            ]]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        return ConversationHandler.END

    elif action == "save":
        # Stara akcja zapisu (bez zdjęć i PDF) - zostawiona dla kompatybilności
        note = pending_notes.get(user_id)
        if note:
            notatka = db.add_notatka(
                telegram_user_id=user_id,
                temat=note["temat"],
                opis=note["opis"],
                transkrypcja=note["transkrypcja"],
                audio_file_id=note["audio_file_id"],
                zadania_list=note["zadania"],
                embedding_vector=note.get("embedding"),
                photo_file_ids=note["photos"] if note["photos"] else None,
                cost_data=note.get("cost_data")  # Dane o kosztach API
            )
            del pending_notes[user_id]

            # Formatuj datę
            data_str = notatka.data_utworzenia.strftime("%d.%m.%Y %H:%M:%S")

            # Komunikat potwierdzający z pełnymi szczegółami
            message = (
                f"🎉 *Notatka zapisana!*\n\n"
                f"🆔 *Numer notatki:* #{notatka.id}\n"
                f"📅 *Data utworzenia:* {data_str}"
            )

            # Przycisk do pobrania transkrypcji
            keyboard = [[
                InlineKeyboardButton("📄 Pobierz transkrypcję (TXT)", callback_data=f"download_transcript_{notatka.id}")
            ]]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        return ConversationHandler.END

    elif action.startswith("download_transcript_"):
        # Pobierz i wyślij transkrypcję jako plik TXT
        try:
            notatka_id = int(action.split("_")[-1])
            notatka = db.get_notatka_by_id(notatka_id, user_id)

            if not notatka:
                await query.answer("❌ Nie znaleziono notatki", show_alert=True)
                return

            await query.answer("📄 Generuję plik TXT...")

            # Utwórz plik TXT z transkrypcją
            import io
            txt_content = f"""TRANSKRYPCJA NOTATKI #{notatka.id}
=====================================

TEMAT:
{notatka.temat}

DATA UTWORZENIA:
{notatka.data_utworzenia.strftime('%d.%m.%Y %H:%M:%S')}

TRANSKRYPCJA:
{notatka.transkrypcja}

=====================================
Wygenerowano przez Voice Notes Bot
"""

            # Utwórz plik w pamięci
            txt_file = io.BytesIO(txt_content.encode('utf-8'))
            txt_file.name = f"transkrypcja_{notatka.id}.txt"

            # Wyślij plik
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=txt_file,
                filename=f"transkrypcja_{notatka.id}.txt",
                caption=f"📄 *Transkrypcja notatki #{notatka.id}*\n📌 {notatka.temat}",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Błąd pobierania transkrypcji: {e}")
            await query.answer("❌ Błąd generowania pliku TXT", show_alert=True)

    elif action == "edit_temat":
        await query.edit_message_text(
            "✏️ Wpisz nowy temat notatki:",
            parse_mode='Markdown'
        )
        return EDITING_TEMAT

    elif action == "cancel":
        if user_id in pending_notes:
            del pending_notes[user_id]
        await query.edit_message_text("❌ Anulowano")
        return ConversationHandler.END

    elif action.startswith("transcript_"):
        # Pokaż pełną transkrypcję
        notatka_id = int(action.split("_")[1])
        notatka = db.get_notatka_by_id(notatka_id, user_id)

        if notatka and notatka.transkrypcja:
            await query.answer()

            # Dla długich transkrypcji (>3000 znaków) - wyślij jako plik
            if len(notatka.transkrypcja) > 3000:
                import tempfile
                import os

                # Utwórz tymczasowy plik
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                    f.write(f"Pełna transkrypcja - Notatka #{notatka.id}\n")
                    f.write(f"Temat: {notatka.temat}\n")
                    f.write(f"Data: {notatka.data_utworzenia.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(notatka.transkrypcja)
                    temp_path = f.name

                # Wyślij plik
                with open(temp_path, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        filename=f"transkrypcja_{notatka.id}.txt",
                        caption=f"📄 *Pełna transkrypcja - Notatka #{notatka.id}*\n📌 {notatka.temat}\n\n({len(notatka.transkrypcja)} znaków)",
                        parse_mode='Markdown'
                    )

                # Usuń tymczasowy plik
                os.remove(temp_path)
            else:
                # Dla krótkich transkrypcji - wyślij jako wiadomość
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"📄 *Pełna transkrypcja - Notatka #{notatka.id}*\n\n{notatka.transkrypcja}",
                    parse_mode='Markdown'
                )
        else:
            await query.answer("❌ Brak transkrypcji", show_alert=True)

    elif action.startswith("download_pdf_"):
        # Generuj i pobierz PDF dla istniejącej notatki
        notatka_id = int(action.split("_")[2])
        notatka = db.get_notatka_by_id(notatka_id, user_id)

        if notatka:
            await query.answer()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📝 Generuję PDF...",
                parse_mode='Markdown'
            )

            try:
                # Generuj PDF z notatki w bazie
                pdf_path = await generate_pdf_from_db(notatka, context)

                # Wyślij PDF
                with open(pdf_path, 'rb') as pdf_file:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=pdf_file,
                        filename=f"notatka_{notatka.id}.pdf",
                        caption=f"📄 *PDF Notatki #{notatka.id}*\n📌 {notatka.temat}",
                        parse_mode='Markdown'
                    )

                # Usuń tymczasowy plik PDF
                import os
                os.remove(pdf_path)

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="✅ *PDF wygenerowany!*",
                    parse_mode='Markdown'
                )

            except Exception as e:
                logger.error(f"Błąd generowania PDF: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ Błąd generowania PDF: {str(e)}",
                    parse_mode='Markdown'
                )
        else:
            await query.answer("❌ Nie znaleziono notatki", show_alert=True)

    elif action.startswith("edit_note_"):
        # Uzupełnij notatkę nagraniem
        notatka_id = int(action.split("_")[2])
        notatka = db.get_notatka_by_id(notatka_id, user_id)

        if notatka:
            await query.answer()
            # Zapisz ID notatki do edycji
            editing_note_id[user_id] = notatka_id

            await query.edit_message_text(
                f"🎤 *Uzupełnianie notatki #{notatka_id}*\n\n"
                f"📌 Temat: {notatka.temat}\n\n"
                f"Wyślij nagranie głosowe lub plik audio, który chcesz dodać do notatki.\n"
                f"Nowe nagranie zostanie transkrybowane i połączone z istniejącą notatką.",
                parse_mode='Markdown'
            )
            return EDITING_NOTE
        else:
            await query.answer("❌ Nie znaleziono notatki", show_alert=True)

    elif action.startswith("play_"):
        # Odsłuchaj notatkę
        notatka_id = int(action.split("_")[1])
        notatka = db.get_notatka_by_id(notatka_id, user_id)

        if notatka:
            await query.answer()
            # Użyj istniejącej funkcji do wysłania pełnej notatki
            # Musimy stworzyć "fake" update z message
            await send_full_note_from_callback(query, context, notatka)
        else:
            await query.answer("❌ Nie znaleziono notatki", show_alert=True)


async def handle_additional_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler dla dodatkowych nagrań w trybie COLLECTING_AUDIO"""
    user_id = update.effective_user.id

    # Pobierz plik audio (voice message lub audio file)
    if update.message.voice:
        audio_obj = update.message.voice
        file_type = "voice"
        filename = "voice.ogg"
    elif update.message.audio:
        audio_obj = update.message.audio
        file_type = "audio"
        filename = update.message.audio.file_name or f"audio.{update.message.audio.mime_type.split('/')[-1]}"
    else:
        await update.message.reply_text("❌ Błąd: Brak pliku audio")
        return COLLECTING_AUDIO

    await update.message.reply_text("🎤 Plik audio otrzymany!")

    try:
        # Pobierz plik
        file = await context.bot.get_file(audio_obj.file_id)
        audio_bytes = await file.download_as_bytearray()

        # Dodaj do kolekcji
        if user_id not in pending_notes:
            pending_notes[user_id] = {
                "audio_parts": [],
                "photos": []
            }

        pending_notes[user_id]["audio_parts"].append({
            "bytes": bytes(audio_bytes),
            "filename": filename,
            "file_id": audio_obj.file_id
        })

        # Zapytaj czy dodać więcej
        part_count = len(pending_notes[user_id]["audio_parts"])
        keyboard = [
            [InlineKeyboardButton("✅ To wszystko - przetwórz", callback_data="finalize_audio")],
            [InlineKeyboardButton("➕ Dodaj więcej nagrań", callback_data="more_audio")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🎤 *Nagrane części: {part_count}*\n\n"
            f"Czy to cała notatka, czy chcesz dodać więcej nagrań?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        return COLLECTING_AUDIO

    except Exception as e:
        logger.error(f"Błąd dodawania audio: {e}")
        await update.message.reply_text(
            f"❌ Wystąpił błąd podczas dodawania:\n`{str(e)}`",
            parse_mode='Markdown'
        )
        return COLLECTING_AUDIO


async def edit_note_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler uzupełniania notatki nagraniem"""
    user_id = update.effective_user.id

    # Sprawdź czy mamy zapisane ID notatki
    if user_id not in editing_note_id:
        await update.message.reply_text("❌ Błąd: Brak notatki do edycji")
        return ConversationHandler.END

    notatka_id = editing_note_id[user_id]
    notatka = db.get_notatka_by_id(notatka_id, user_id)

    if not notatka:
        await update.message.reply_text("❌ Nie znaleziono notatki")
        del editing_note_id[user_id]
        return ConversationHandler.END

    # Pobierz plik audio
    if update.message.voice:
        audio_obj = update.message.voice
        filename = "voice.ogg"
    elif update.message.audio:
        audio_obj = update.message.audio
        filename = update.message.audio.file_name or f"audio.{update.message.audio.mime_type.split('/')[-1]}"
    else:
        await update.message.reply_text("❌ Błąd: Brak pliku audio")
        return EDITING_NOTE

    await update.message.reply_text("🔄 Przetwarzam nagranie...")

    try:
        # Pobierz plik
        file = await context.bot.get_file(audio_obj.file_id)
        audio_bytes = await file.download_as_bytearray()

        # Transkrybuj nowe nagranie
        await update.message.reply_text("🔄 Transkrybuję nowe nagranie...")
        new_transcript, audio_duration = ai.transcribe_audio(bytes(audio_bytes), filename=filename)

        # Dodaj timestamp edycji
        edit_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Połącz z poprzednią transkrypcją z adnotacją
        old_transcript = notatka.transkrypcja or ""
        combined_transcript = old_transcript + f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n📝 Edit - {edit_timestamp} - uzupełnienie\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{new_transcript}"

        # Ponowna analiza struktury
        await update.message.reply_text("🤖 Analizuję zaktualizowaną treść...")
        structure, gpt_usage = ai.extract_structure(combined_transcript)

        # Dodaj informację o edycji do opisu
        updated_opis = structure["opis"] + f"\n\n---\n✏️ *Edytowano:* {edit_timestamp}"

        # Generuj nowy embedding
        embedding_text = f"{structure['temat']}. {structure['opis']}"
        embedding, embedding_tokens = ai.get_embedding(embedding_text)

        # Oblicz dodatkowe koszty
        from cost_calculator import CostCalculator

        cost_whisper = CostCalculator.calculate_whisper_cost(audio_duration)
        cost_gpt_in, cost_gpt_out, cost_gpt_total = CostCalculator.calculate_gpt_cost(
            gpt_usage['input_tokens'],
            gpt_usage['output_tokens']
        )
        cost_embedding = CostCalculator.calculate_embedding_cost(embedding_tokens)

        additional_costs = {
            "audio_duration_seconds": audio_duration,
            "tokens_input": gpt_usage['input_tokens'],
            "tokens_output": gpt_usage['output_tokens'],
            "tokens_embedding": embedding_tokens,
            "cost_whisper_usd": cost_whisper,
            "cost_gpt_input_usd": cost_gpt_in,
            "cost_gpt_output_usd": cost_gpt_out,
            "cost_embedding_usd": cost_embedding
        }

        # Aktualizuj notatkę w bazie
        updated_notatka = db.update_notatka(
            notatka_id=notatka_id,
            telegram_user_id=user_id,
            temat=structure["temat"],
            opis=updated_opis,  # Opis z informacją o edycji
            transkrypcja=combined_transcript,
            zadania_list=structure["zadania"],
            embedding_vector=embedding,
            additional_cost_data=additional_costs
        )

        if updated_notatka:
            # Pokaż koszt
            cost_total = CostCalculator.calculate_total_cost(
                cost_whisper, cost_gpt_in, cost_gpt_out, cost_embedding
            )

            await update.message.reply_text(
                f"✅ *Notatka #{notatka_id} zaktualizowana!*\n\n"
                f"📌 Temat: {structure['temat']}\n"
                f"✏️ Edytowano: {edit_timestamp}\n"
                f"💰 Koszt uzupełnienia: {CostCalculator.format_cost_usd(cost_total)}",
                parse_mode='Markdown'
            )

            # Wyślij pełną zaktualizowaną notatkę
            await send_full_note(update, context, updated_notatka)
        else:
            await update.message.reply_text("❌ Błąd aktualizacji notatki")

        # Wyczyść stan edycji
        del editing_note_id[user_id]
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Błąd uzupełniania notatki: {e}")
        await update.message.reply_text(
            f"❌ Wystąpił błąd podczas uzupełniania:\n`{str(e)}`",
            parse_mode='Markdown'
        )
        # Wyczyść stan edycji
        if user_id in editing_note_id:
            del editing_note_id[user_id]
        return ConversationHandler.END


async def edit_temat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler edycji tematu"""
    user_id = update.effective_user.id
    new_temat = update.message.text

    if user_id in pending_notes:
        pending_notes[user_id]["temat"] = new_temat
        await update.message.reply_text("✅ Temat zaktualizowany!")
        await show_note_preview(update, user_id)

    return WAITING_CONFIRMATION


@check_user_allowed
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /lista"""
    user_id = update.effective_user.id
    notatki = db.get_notatki(user_id, limit=10)

    if not notatki:
        await update.message.reply_text("📭 Nie masz jeszcze żadnych notatek!")
        return

    message = "📚 *Twoje ostatnie notatki:*\n\n"
    for notatka in notatki:
        data_str = notatka.data_utworzenia.strftime("%Y-%m-%d %H:%M")
        zadania_count = len(notatka.zadania)
        zadania_info = f" ({zadania_count} zadań)" if zadania_count > 0 else ""

        message += (
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: {notatka.id}\n"
            f"📅 {data_str}\n"
            f"📌 *{notatka.temat}*{zadania_info}\n"
            f"📝 {notatka.opis[:100]}{'...' if len(notatka.opis) > 100 else ''}\n"
        )

    message += "\n💡 Użyj `/notatka [id]` aby odsłuchać i zobaczyć pełną notatkę"

    await update.message.reply_text(message, parse_mode='Markdown')


@check_user_allowed
async def szukaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /szukaj"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❓ Użycie: `/szukaj [słowo kluczowe]`", parse_mode='Markdown')
        return

    query = " ".join(context.args)
    notatki = db.search_notatki(user_id, query)

    if not notatki:
        await update.message.reply_text(f"🔍 Nie znaleziono notatek dla: *{query}*", parse_mode='Markdown')
        return

    message = f"🔍 *Wyniki dla: {query}*\n\n"
    for notatka in notatki[:5]:  # Max 5 wyników
        data_str = notatka.data_utworzenia.strftime("%Y-%m-%d %H:%M")
        message += (
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: {notatka.id}\n"
            f"📅 {data_str}\n"
            f"📌 *{notatka.temat}*\n"
            f"📝 {notatka.opis[:150]}{'...' if len(notatka.opis) > 150 else ''}\n"
        )

    await update.message.reply_text(message, parse_mode='Markdown')


@check_user_allowed
async def zadania(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /zadania"""
    user_id = update.effective_user.id
    zadania_list = db.get_wszystkie_zadania(user_id, tylko_niewykonane=True)

    if not zadania_list:
        await update.message.reply_text("✅ Nie masz żadnych zadań do zrobienia!")
        return

    message = "📋 *Zadania do zrobienia:*\n\n"
    for zadanie in zadania_list:
        message += f"⬜ `{zadanie.id}`: {zadanie.zadanie}\n"

    message += f"\n💡 Użyj `/wykonane [id]` aby oznaczyć zadanie jako wykonane"

    await update.message.reply_text(message, parse_mode='Markdown')


@check_user_allowed
async def wykonane(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /wykonane"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❓ Użycie: `/wykonane [id zadania]`", parse_mode='Markdown')
        return

    try:
        zadanie_id = int(context.args[0])
        success = db.oznacz_zadanie_wykonane(zadanie_id, user_id)

        if success:
            await update.message.reply_text(f"✅ Zadanie #{zadanie_id} oznaczone jako wykonane!")
        else:
            await update.message.reply_text(f"❌ Nie znaleziono zadania #{zadanie_id}")

    except ValueError:
        await update.message.reply_text("❌ ID zadania musi być liczbą!")


@check_user_allowed
async def notatka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /notatka [id]"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❓ Użycie: `/notatka [id]`\nPobierz ID z `/lista`", parse_mode='Markdown')
        return

    try:
        notatka_id = int(context.args[0])
        notatka = db.get_notatka_by_id(notatka_id, user_id)

        if not notatka:
            await update.message.reply_text(f"❌ Nie znaleziono notatki #{notatka_id}")
            return

        # Formatuj notatę
        await send_full_note(update, context, notatka)

    except ValueError:
        await update.message.reply_text("❌ ID notatki musi być liczbą!")


@check_user_allowed
async def ostatnia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /ostatnia"""
    user_id = update.effective_user.id
    notatki = db.get_notatki(user_id, limit=1)

    if not notatki:
        await update.message.reply_text("📭 Nie masz jeszcze żadnych notatek!")
        return

    notatka = notatki[0]
    await send_full_note(update, context, notatka)


async def send_full_note(update: Update, context: ContextTypes.DEFAULT_TYPE, notatka):
    """Wysyła pełną notatkę z audio i przyciskami"""
    data_str = notatka.data_utworzenia.strftime("%Y-%m-%d %H:%M:%S")

    # Formatuj zadania
    zadania_text = ""
    if notatka.zadania:
        zadania_text = "\n\n📋 *ZADANIA:*\n"
        for i, zadanie in enumerate(notatka.zadania, 1):
            status = "✅" if zadanie.wykonane else "⬜"
            zadania_text += f"{status} `{zadanie.id}`: {zadanie.zadanie}\n"
    else:
        zadania_text = "\n\n📋 *ZADANIA:* brak"

    # Główna wiadomość
    message = (
        f"🆔 *Notatka #{notatka.id}*\n"
        f"📅 {data_str}\n\n"
        f"📌 *TEMAT:*\n{notatka.temat}\n\n"
        f"📝 *OPIS:*\n{notatka.opis}"
        f"{zadania_text}"
    )

    # Przyciski
    keyboard = []

    # Przycisk do pełnej transkrypcji (jeśli jest dłuższa niż opis)
    if notatka.transkrypcja and len(notatka.transkrypcja) > len(notatka.opis):
        keyboard.append([InlineKeyboardButton("📄 Pełna transkrypcja", callback_data=f"transcript_{notatka.id}")])

    # Przycisk do pobrania transkrypcji jako TXT
    keyboard.append([InlineKeyboardButton("📥 Pobierz transkrypcję (TXT)", callback_data=f"download_transcript_{notatka.id}")])

    # Przycisk do uzupełnienia notatki nagraniem
    keyboard.append([InlineKeyboardButton("🎤 Uzupełnij nagraniem", callback_data=f"edit_note_{notatka.id}")])

    # Przycisk do generowania PDF
    keyboard.append([InlineKeyboardButton("📄 Generuj PDF", callback_data=f"download_pdf_{notatka.id}")])

    # Wyślij wiadomość
    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, parse_mode='Markdown')

    # ========================================
    # WYSYŁANIE AUDIO - WYŁĄCZONE (oszczędność miejsca)
    # Aby włączyć: odkomentuj poniższy blok
    # ========================================
    # if notatka.audio_file_id:
    #     try:
    #         await context.bot.send_voice(
    #             chat_id=update.effective_chat.id,
    #             voice=notatka.audio_file_id,
    #             caption="🎧 Oryginalne nagranie"
    #         )
    #     except Exception as e:
    #         logger.error(f"Błąd wysyłania audio: {e}")
    #         await update.message.reply_text("⚠️ Nie mogę wysłać nagrania audio (plik wygasł)")


async def send_full_note_from_callback(query, context: ContextTypes.DEFAULT_TYPE, notatka):
    """Wysyła pełną notatkę z audio - wersja dla callback query"""
    data_str = notatka.data_utworzenia.strftime("%Y-%m-%d %H:%M:%S")

    # Formatuj zadania
    zadania_text = ""
    if notatka.zadania:
        zadania_text = "\n\n📋 *ZADANIA:*\n"
        for i, zadanie in enumerate(notatka.zadania, 1):
            status = "✅" if zadanie.wykonane else "⬜"
            zadania_text += f"{status} `{zadanie.id}`: {zadanie.zadanie}\n"
    else:
        zadania_text = "\n\n📋 *ZADANIA:* brak"

    # Główna wiadomość
    message = (
        f"🆔 *Notatka #{notatka.id}*\n"
        f"📅 {data_str}\n\n"
        f"📌 *TEMAT:*\n{notatka.temat}\n\n"
        f"📝 *OPIS:*\n{notatka.opis}"
        f"{zadania_text}"
    )

    # Przyciski
    keyboard = []

    # Przycisk do pełnej transkrypcji (jeśli jest dłuższa niż opis)
    if notatka.transkrypcja and len(notatka.transkrypcja) > len(notatka.opis):
        keyboard.append([InlineKeyboardButton("📄 Pełna transkrypcja", callback_data=f"transcript_{notatka.id}")])

    # Przycisk do pobrania transkrypcji jako TXT
    keyboard.append([InlineKeyboardButton("📥 Pobierz transkrypcję (TXT)", callback_data=f"download_transcript_{notatka.id}")])

    # Przycisk do uzupełnienia notatki nagraniem
    keyboard.append([InlineKeyboardButton("🎤 Uzupełnij nagraniem", callback_data=f"edit_note_{notatka.id}")])

    # Przycisk do generowania PDF
    keyboard.append([InlineKeyboardButton("📄 Generuj PDF", callback_data=f"download_pdf_{notatka.id}")])

    # Wyślij wiadomość
    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message,
            parse_mode='Markdown'
        )

    # ========================================
    # WYSYŁANIE AUDIO - WYŁĄCZONE (oszczędność miejsca)
    # Aby włączyć: odkomentuj poniższy blok
    # ========================================
    # if notatka.audio_file_id:
    #     try:
    #         await context.bot.send_voice(
    #             chat_id=query.message.chat_id,
    #             voice=notatka.audio_file_id,
    #             caption="🎧 Oryginalne nagranie"
    #         )
    #     except Exception as e:
    #         logger.error(f"Błąd wysyłania audio: {e}")
    #         await context.bot.send_message(
    #             chat_id=query.message.chat_id,
    #             text="⚠️ Nie mogę wysłać nagrania audio (plik wygasł)"
    #         )


@check_user_allowed
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /stats"""
    user_id = update.effective_user.id
    statystyki = db.get_statystyki(user_id)

    # Podstawowe statystyki
    message = (
        "📊 *Twoje statystyki:*\n\n"
        f"📝 Notatki: *{statystyki['notatki']}*\n"
        f"📋 Zadania wszystkie: *{statystyki['zadania_wszystkie']}*\n"
        f"✅ Wykonane: *{statystyki['zadania_wykonane']}*\n"
        f"⬜ Do zrobienia: *{statystyki['zadania_do_zrobienia']}*\n"
    )

    # Statystyki kosztów API
    if statystyki.get('koszty'):
        from cost_calculator import CostCalculator
        costs = statystyki['koszty']

        if costs['notes_with_costs'] > 0:
            message += (
                "\n💰 *Koszty API OpenAI:*\n"
                "━━━━━━━━━━━━━━━━━\n"
                f"Łącznie: *{CostCalculator.format_cost_usd(costs['total_usd'])}*\n"
                f"├─ Whisper: {CostCalculator.format_cost_usd(costs['total_whisper_usd'])}\n"
                f"├─ GPT-4o-mini: {CostCalculator.format_cost_usd(costs['total_gpt_usd'])}\n"
                f"└─ Embeddings: {CostCalculator.format_cost_usd(costs['total_embedding_usd'])}\n\n"
                f"📈 Średnio/notatka: *{CostCalculator.format_cost_usd(costs['average_per_note_usd'])}*\n"
                f"📊 Notatek z kosztami: {costs['notes_with_costs']}/{statystyki['notatki']}\n"
            )

    await update.message.reply_text(message, parse_mode='Markdown')


async def generate_pdf_from_db(notatka, context):
    """
    Generuje PDF dla istniejącej notatki z bazy danych

    Args:
        notatka: Obiekt Notatka z bazy danych
        context: Context bota

    Returns:
        str: Ścieżka do wygenerowanego pliku PDF
    """
    import json

    # Konwertuj obiekt Notatka do formatu dict (jak w pending_notes)
    note_dict = {
        "temat": notatka.temat,
        "opis": notatka.opis,
        "transkrypcja": notatka.transkrypcja,
        "zadania": [z.zadanie for z in notatka.zadania] if notatka.zadania else [],
        "photos": json.loads(notatka.photo_file_ids) if notatka.photo_file_ids else []
    }

    # Użyj istniejącej funkcji generate_pdf
    return await generate_pdf(note_dict, notatka.id, context)


async def generate_pdf(note, notatka_id, context):
    """
    Generuje sformatowany PDF z notatki

    Args:
        note: Słownik z danymi notatki (pending_notes)
        notatka_id: ID notatki w bazie danych
        context: Context bota (do pobierania zdjęć)

    Returns:
        str: Ścieżka do wygenerowanego pliku PDF
    """
    from weasyprint import HTML, CSS
    from datetime import datetime
    import tempfile
    import base64

    # Utwórz tymczasowy katalog na obrazy
    temp_dir = tempfile.mkdtemp()
    pdf_path = f"{temp_dir}/notatka_{notatka_id}.pdf"

    # Pobierz zdjęcia i przekonwertuj na base64
    photos_html = ""
    if note["photos"]:
        photos_html = "<div class='photos'><h2>📸 Zdjęcia</h2>"

        for i, photo_file_id in enumerate(note["photos"], 1):
            try:
                # Pobierz zdjęcie z Telegram
                photo_file = await context.bot.get_file(photo_file_id)
                photo_bytes = await photo_file.download_as_bytearray()

                # Konwertuj do base64
                photo_base64 = base64.b64encode(bytes(photo_bytes)).decode('utf-8')

                # Dodaj do HTML jako inline image
                photos_html += f'<img src="data:image/jpeg;base64,{photo_base64}" alt="Zdjęcie {i}" />'

            except Exception as e:
                logger.error(f"Błąd pobierania zdjęcia {i}: {e}")
                photos_html += f'<p class="error">❌ Błąd wczytywania zdjęcia {i}</p>'

        photos_html += "</div>"

    # Formatuj zadania
    zadania_html = ""
    if note["zadania"]:
        zadania_html = "<div class='zadania'><h2>📋 Zadania</h2><ul>"
        for zadanie in note["zadania"]:
            zadania_html += f"<li>{zadanie}</li>"
        zadania_html += "</ul></div>"

    # Szablon HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Notatka #{notatka_id}</title>
    </head>
    <body>
        <div class="header">
            <h1>📝 Notatka #{notatka_id}</h1>
            <p class="date">📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="content">
            <div class="section">
                <h2>📌 Temat</h2>
                <p class="temat">{note['temat']}</p>
            </div>

            <div class="section">
                <h2>📝 Opis</h2>
                <p class="opis">{note['opis']}</p>
            </div>

            {zadania_html}

            {photos_html}
        </div>

        <div class="footer">
            <p>Wygenerowano przez Voice Notes Bot</p>
        </div>
    </body>
    </html>
    """

    # CSS dla ładnego formatowania
    css_content = """
    @page {
        size: A4;
        margin: 2cm;
    }

    body {
        font-family: 'DejaVu Sans', Arial, sans-serif;
        font-size: 12pt;
        line-height: 1.6;
        color: #333;
    }

    .header {
        text-align: center;
        border-bottom: 3px solid #4CAF50;
        padding-bottom: 20px;
        margin-bottom: 30px;
    }

    .header h1 {
        color: #4CAF50;
        font-size: 28pt;
        margin: 0;
    }

    .date {
        color: #666;
        font-size: 11pt;
        margin-top: 10px;
    }

    .section {
        margin-bottom: 30px;
    }

    h2 {
        color: #2196F3;
        font-size: 16pt;
        border-bottom: 2px solid #E3F2FD;
        padding-bottom: 5px;
        margin-bottom: 15px;
    }

    .temat {
        font-size: 14pt;
        font-weight: bold;
        color: #333;
    }

    .opis {
        text-align: justify;
        white-space: pre-wrap;
    }

    .zadania ul {
        list-style-type: none;
        padding-left: 0;
    }

    .zadania li {
        padding: 10px;
        margin: 5px 0;
        background-color: #FFF9C4;
        border-left: 4px solid #FBC02D;
        border-radius: 4px;
    }

    .zadania li::before {
        content: "☐ ";
        font-weight: bold;
        color: #FBC02D;
    }

    .photos {
        margin-top: 30px;
    }

    .photos img {
        max-width: 100%;
        height: auto;
        margin: 10px 0;
        border: 1px solid #ddd;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        page-break-inside: avoid;
    }

    .error {
        color: #f44336;
        font-style: italic;
    }

    .footer {
        margin-top: 50px;
        text-align: center;
        font-size: 10pt;
        color: #999;
        border-top: 1px solid #ddd;
        padding-top: 20px;
    }
    """

    # Generuj PDF
    html = HTML(string=html_content)
    css = CSS(string=css_content)

    # write_pdf() zwraca bytes, zapisz do pliku
    pdf_bytes = html.write_pdf(stylesheets=[css])

    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)

    return pdf_path


def main():
    """Główna funkcja uruchamiająca bota"""
    # Walidacja konfiguracji
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Błąd konfiguracji: {e}")
        return

    # Tworzenie aplikacji
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler dla voice notes i audio files
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.VOICE | filters.AUDIO, handle_voice)],
        states={
            COLLECTING_AUDIO: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_additional_voice),
                CallbackQueryHandler(button_handler)
            ],
            WAITING_CONFIRMATION: [CallbackQueryHandler(button_handler)],
            EDITING_TEMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_temat)],
            WAITING_PHOTOS: [
                MessageHandler(filters.PHOTO, handle_photo),
                CallbackQueryHandler(button_handler)
            ],
            ASKING_PDF: [CallbackQueryHandler(button_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Conversation handler dla edycji notatek nagraniem
    edit_note_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^edit_note_")],
        states={
            EDITING_NOTE: [MessageHandler(filters.VOICE | filters.AUDIO, edit_note_audio)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Dodanie handlerów
    application.add_handler(CommandHandler("start", start))
    application.add_handler(edit_note_conv_handler)  # Handler edycji notatek - PRZED głównym!
    application.add_handler(conv_handler)  # Główny handler
    application.add_handler(CommandHandler("lista", lista))
    application.add_handler(CommandHandler("notatka", notatka))
    application.add_handler(CommandHandler("ostatnia", ostatnia))
    application.add_handler(CommandHandler("szukaj", szukaj))
    application.add_handler(CommandHandler("zadania", zadania))
    application.add_handler(CommandHandler("wykonane", wykonane))
    application.add_handler(CommandHandler("stats", stats))

    # Handler dla przycisków (poza conversation handler)
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^transcript_"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^download_pdf_"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^download_transcript_"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^play_"))

    # Uruchomienie bota
    logger.info("🚀 Bot uruchomiony!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
