import json
import httpx
from datetime import datetime, timedelta
import re

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

GUESTS = {
    "ברקת": "bareket.barnatan@wsc-sports.com"
}


async def parse_event_from_text(text: str) -> dict | None:
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    day_name_he = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"][today.weekday()]

    prompt = f"""היום הוא {today_str} (יום {day_name_he}).

נתח את ההודעה הבאה ומצא פרטי אירוע:
"{text}"

החזר JSON בלבד (ללא טקסט נוסף) עם השדות הבאים:
{{
  "summary": "כותרת האירוע",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "duration_hours": 1,
  "guest": null
}}

חוקים:
- "מחר" = {(today + timedelta(days=1)).strftime("%Y-%m-%d")}
- "היום" = {today_str}
- אם נאמר "יום שני/שלישי..." - חשב את התאריך הקרוב הבא
- אם אין שעה - השתמש ב-09:00
- אם אין משך - השתמש ב-1 שעה
- אם כתוב "כולל ברקת" - שים guest: "ברקת"
- אם לא מצאת מספיק מידע, החזר null
"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-3-5-20241022",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)
        response.raise_for_status()
        data = response.json()

    content = data["content"][0]["text"].strip()

    if content.lower() == "null":
        return None

    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if not json_match:
        return None

    parsed = json.loads(json_match.group())

    date_str = parsed["date"]
    time_str = parsed["time"]
    duration = float(parsed.get("duration_hours", 1))

    start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(hours=duration)

    day_names = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    day_display = day_names[start_dt.weekday()]
    date_display = start_dt.strftime(f"יום {day_display}, %d/%m/%Y")

    # Resolve guest name to email
    guest_email = None
    guest_name = parsed.get("guest")
    if guest_name and guest_name in GUESTS:
        guest_email = GUESTS[guest_name]

    return {
        "summary": parsed["summary"],
        "start_datetime": start_dt,
        "end_datetime": end_dt,
        "date_str": date_display,
        "time_str": f"{time_str} - {end_dt.strftime('%H:%M')}",
        "duration_hours": duration,
        "guest_email": guest_email,
        "guest_name": guest_name
    }
