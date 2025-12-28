"""
Telegram Bot do notatek głosowych z automatyczną ekstrakcją struktury przez AI
"""
import logging
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
WAITING_CONFIRMATION, EDITING_TEMAT, EDITING_OPIS = range(3)

# Globalne instancje
db = Database()
ai = AIProcessor()

# Tymczasowe dane notatki (w sesji użytkownika)
pending_notes = {}


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


@check_user_allowed
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /start"""
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

        # Transkrypcja dla wykrycia keywordu
        await update.message.reply_text("🔄 Transkrybuję audio...")
        transcription = ai.transcribe_audio(bytes(audio_bytes), filename=filename)

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

        # W przeciwnym razie - normalne przetwarzanie notatki
        await update.message.reply_text("🤖 Analizuję notatkę...")

        # Przetwarzanie przez AI (z transkrypcją już gotową)
        structure = ai.extract_structure(transcription)

        # Generowanie embedding
        embedding_text = f"{structure['temat']}. {structure['opis']}"
        embedding = ai.get_embedding(embedding_text)

        # Zapisz do pending
        pending_notes[user_id] = {
            "audio_file_id": audio_obj.file_id,
            "transkrypcja": transcription,
            "temat": structure["temat"],
            "opis": structure["opis"],
            "zadania": structure["zadania"],
            "embedding": embedding
        }

        # Pokaż wynik do zatwierdzenia
        await show_note_preview(update, user_id)

        return WAITING_CONFIRMATION

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

        # Generuj embedding dla query
        query_embedding = ai.get_embedding(search_query)

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
        "💾 Zapisać tę notatkę?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Zapisz", callback_data="save"),
            InlineKeyboardButton("✏️ Edytuj temat", callback_data="edit_temat")
        ],
        [
            InlineKeyboardButton("❌ Anuluj", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler przycisków inline"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    action = query.data

    if action == "save":
        # Zapisz notatkę
        note = pending_notes.get(user_id)
        if note:
            db.add_notatka(
                telegram_user_id=user_id,
                temat=note["temat"],
                opis=note["opis"],
                transkrypcja=note["transkrypcja"],
                audio_file_id=note["audio_file_id"],
                zadania_list=note["zadania"],
                embedding_vector=note.get("embedding")
            )
            del pending_notes[user_id]
            await query.edit_message_text("🎉 *Notatka zapisana!*", parse_mode='Markdown')
        return ConversationHandler.END

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
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📄 *Pełna transkrypcja - Notatka #{notatka.id}*\n\n{notatka.transkrypcja}",
                parse_mode='Markdown'
            )
        else:
            await query.answer("❌ Brak transkrypcji", show_alert=True)

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

    # Wyślij wiadomość
    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, parse_mode='Markdown')

    # Wyślij audio jeśli jest
    if notatka.audio_file_id:
        try:
            await context.bot.send_voice(
                chat_id=update.effective_chat.id,
                voice=notatka.audio_file_id,
                caption="🎧 Oryginalne nagranie"
            )
        except Exception as e:
            logger.error(f"Błąd wysyłania audio: {e}")
            await update.message.reply_text("⚠️ Nie mogę wysłać nagrania audio (plik wygasł)")


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

    # Wyślij audio jeśli jest
    if notatka.audio_file_id:
        try:
            await context.bot.send_voice(
                chat_id=query.message.chat_id,
                voice=notatka.audio_file_id,
                caption="🎧 Oryginalne nagranie"
            )
        except Exception as e:
            logger.error(f"Błąd wysyłania audio: {e}")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="⚠️ Nie mogę wysłać nagrania audio (plik wygasł)"
            )


@check_user_allowed
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler komendy /stats"""
    user_id = update.effective_user.id
    statystyki = db.get_statystyki(user_id)

    message = (
        "📊 *Twoje statystyki:*\n\n"
        f"📝 Notatki: *{statystyki['notatki']}*\n"
        f"📋 Zadania wszystkie: *{statystyki['zadania_wszystkie']}*\n"
        f"✅ Wykonane: *{statystyki['zadania_wykonane']}*\n"
        f"⬜ Do zrobienia: *{statystyki['zadania_do_zrobienia']}*\n"
    )

    await update.message.reply_text(message, parse_mode='Markdown')


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
            WAITING_CONFIRMATION: [CallbackQueryHandler(button_handler)],
            EDITING_TEMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_temat)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Dodanie handlerów
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("lista", lista))
    application.add_handler(CommandHandler("notatka", notatka))
    application.add_handler(CommandHandler("ostatnia", ostatnia))
    application.add_handler(CommandHandler("szukaj", szukaj))
    application.add_handler(CommandHandler("zadania", zadania))
    application.add_handler(CommandHandler("wykonane", wykonane))
    application.add_handler(CommandHandler("stats", stats))

    # Handler dla przycisków (poza conversation handler)
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^transcript_"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^play_"))

    # Uruchomienie bota
    logger.info("🚀 Bot uruchomiony!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
