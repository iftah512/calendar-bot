import logging
import os
import asyncio
import httpx
from calendar_utils import add_event_to_calendar
from event_parser import parse_event_from_text

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


async def send_message(chat_id, text, parse_mode="Markdown"):
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        })


async def handle_update(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
        await send_message(chat_id, "⛔ אין לך הרשאה להשתמש בבוט זה.")
        return

    if text == "/start":
        await send_message(chat_id,
            "👋 שלום! אני הבוט שלך ליומן.\n\n"
            "שלח לי הודעה עם פרטי הפגישה, לדוגמה:\n"
            "• *פגישה עם דן ביום שלישי ב-15:00*\n"
            "• *ישיבת צוות מחר ב-10:00*\n\n"
            "ואני אוסיף אותה ל-Google Calendar שלך! 📅"
        )
        return

    await send_message(chat_id, "⏳ מעבד את ההודעה...")

    try:
        event = await parse_event_from_text(text)

        if not event:
            await send_message(chat_id,
                "❌ לא הצלחתי לזהות פרטי אירוע.\n"
                "נסה לכלול תאריך/יום ושעה, לדוגמה:\n"
                "*פגישה עם יוסי מחר ב-14:00*"
            )
            return

        event_link = add_event_to_calendar(event)
        guest_line = f"\n👤 זימון נשלח ל: {event['guest_name']}" if event.get('guest_email') else ""

        await send_message(chat_id,
            f"✅ נוסף ליומן!\n\n"
            f"📌 *{event['summary']}*\n"
            f"📅 {event['date_str']}\n"
            f"⏰ {event['time_str']}\n"
            f"⏱ משך: {event['duration_hours']} שעה"
            f"{guest_line}\n\n"
            f"🔗 [פתח באירוע]({event_link})"
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        await send_message(chat_id, f"❌ שגיאה: {str(e)}")


async def main():
    logger.info("Bot is running...")
    offset = 0

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            try:
                response = await client.get(f"{BASE_URL}/getUpdates", params={
                    "offset": offset,
                    "timeout": 20
                }, timeout=25)
                data = response.json()

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    await handle_update(update)

            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
