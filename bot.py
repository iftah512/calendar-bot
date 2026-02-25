import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from calendar_utils import add_event_to_calendar
from event_parser import parse_event_from_text

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))  # Your Telegram user ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 שלום! אני הבוט שלך ליומן.\n\n"
        "שלח לי הודעה עם פרטי הפגישה, לדוגמה:\n"
        "• *פגישה עם דן ביום שלישי ב-15:00*\n"
        "• *ישיבת צוות מחר ב-10:00 לשעה*\n"
        "• *רופא שיניים 25/12 ב-9:30*\n\n"
        "ואני אוסיף אותה ל-Google Calendar שלך! 📅",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Security: only allow your own user
    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ אין לך הרשאה להשתמש בבוט זה.")
        return

    text = update.message.text
    await update.message.reply_text("⏳ מעבד את ההודעה...")

    try:
        event = await parse_event_from_text(text)

        if not event:
            await update.message.reply_text(
                "❌ לא הצלחתי לזהות פרטי אירוע בהודעה.\n"
                "נסה לכלול תאריך/יום ושעה, לדוגמה:\n"
                "*פגישה עם יוסי מחר ב-14:00*",
                parse_mode="Markdown"
            )
            return

        event_link = add_event_to_calendar(event)

        guest_line = f"\n👤 זימון נשלח ל: {event['guest_name']}" if event.get('guest_email') else ""

        await update.message.reply_text(
            f"✅ נוסף ליומן!\n\n"
            f"📌 *{event['summary']}*\n"
            f"📅 {event['date_str']}\n"
            f"⏰ {event['time_str']}\n"
            f"⏱ משך: {event['duration_hours']} שעה"
            f"{guest_line}\n\n"
            f"🔗 [פתח באירוע]({event_link})",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(f"❌ שגיאה: {str(e)}")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
