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
        "📝 *Jak używać:*\n"
        "• Wyślij mi *voice message* - automatycznie stworzę notatkę!\n"
        "• `/lista` - zobacz ostatnie notatki\n"
        "• `/szukaj [słowo]` - wyszukaj notatki\n"
        "• `/zadania` - zobacz zadania do zrobienia\n"
        "• `/wykonane [id]` - oznacz zadanie jako wykonane\n"
        "• `/stats` - statystyki\n\n"
        "✨ Bot automatycznie wyciągnie temat, opis i zadania z Twojej notatki!",
        parse_mode='Markdown'
    )


@check_user_allowed
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler notatek głosowych"""
    user_id = update.effective_user.id

    # Pobierz plik audio
    voice = update.message.voice
    await update.message.reply_text("🎤 Nagranie otrzymane! Przetwarzam...")

    try:
        # Pobierz plik
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()

        # Informacja o transkrypcji
        await update.message.reply_text("🔄 Transkrybuję audio...")

        # Przetwarzanie przez AI
        result = ai.process_voice_note(bytes(audio_bytes), filename="voice.ogg")

        # Zapisz do pending
        pending_notes[user_id] = {
            "audio_file_id": voice.file_id,
            "transkrypcja": result["transkrypcja"],
            "temat": result["temat"],
            "opis": result["opis"],
            "zadania": result["zadania"]
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
                zadania_list=note["zadania"]
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

    # Conversation handler dla voice notes
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.VOICE, handle_voice)],
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
    application.add_handler(CommandHandler("szukaj", szukaj))
    application.add_handler(CommandHandler("zadania", zadania))
    application.add_handler(CommandHandler("wykonane", wykonane))
    application.add_handler(CommandHandler("stats", stats))

    # Uruchomienie bota
    logger.info("🚀 Bot uruchomiony!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
