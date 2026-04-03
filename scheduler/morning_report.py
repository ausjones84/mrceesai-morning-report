import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import json
import os
import urllib.request
import tempfile

# pip install gTTS — free Google Text-to-Speech, no API key needed
from gtts import gTTS

# ─── Credentials from GitHub Secrets ───────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GOOGLE_CREDS     = os.environ["GOOGLE_CREDS"]
SHEET_NAME       = os.environ["SHEET_NAME"]

HEADERS = [
    "Timestamp", "First Name", "Last Name", "Email", "Phone",
    "City", "Website", "LinkedIn", "Instagram", "Facebook", "X/Twitter",
    "Business Name", "Industry", "Elevator Pitch", "Years in Business",
    "Ideal Referral", "Top Clients", "How Heard", "Invited By",
    "Looking For", "BNI Experience", "Biggest Challenge", "Interest Level", "Notes"
]

# ─── Daily Task Checklist (from MrCeesAI Money-First Roadmap) ──────────────────
# These rotate based on which systems are active. Edit as you complete systems.
DAILY_TASKS = [
    "Check Gmail for BNI hot lead replies and outreach responses.",
    "Review any new no-website business leads scraped overnight.",
    "Check SAM dot gov for new government contract opportunities.",
    "Approve today's YouTube AI twin video script for HeyGen.",
    "Review LinkedIn for new cloud engineering job matches.",
    "Follow up with any leads marked due today in your outreach sheet.",
    "Check TechPassportApp for new signups or support messages.",
    "Post or schedule one piece of content on social media.",
]

WEEKLY_TASKS = {
    0: "Monday — Start the week strong. Review your full pipeline and set your top 3 revenue goals for this week.",
    1: "Tuesday — Focus on outreach. Send new no-website cold emails and follow up on SAM dot gov leads.",
    2: "Wednesday — Content day. Review and finalize YouTube scripts. Record or approve HeyGen videos.",
    3: "Thursday — BNI report arrives at 8:30 A M. Review it, follow up with hot leads from the week, and prepare for tomorrow's meeting.",
    4: "Friday — BNI meeting day. Share your form link. Close out the week's outreach. Review what moved forward.",
    5: "Saturday — Builder day. Work on TechPassport App, Academy backend, or digital products.",
    6: "Sunday — Plan ahead. Set your priorities for Monday morning and prep your content calendar.",
}

# ─── Telegram Helpers ──────────────────────────────────────────────────────────

def send_telegram_text(message):
    """Send a text message to Austin's Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return r.read()


def send_telegram_voice(audio_path):
    """Send an audio file as a Telegram voice message (OGG format)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVoice"

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    boundary = "----BNIFormBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{TELEGRAM_CHAT_ID}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="voice"; filename="morning_report.ogg"\r\n'
        f"Content-Type: audio/ogg\r\n\r\n"
    ).encode("utf-8") + audio_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req) as r:
        return r.read()


# ─── Google Sheets Data ────────────────────────────────────────────────────────

def get_sheet_data():
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_CREDS),
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet.get_all_values()


def get_recent_visitors(all_rows, days=1):
    if len(all_rows) <= 1:
        return []
    cutoff = datetime.now() - timedelta(days=days)
    visitors = []
    for row in all_rows[1:]:
        try:
            row_dict = dict(zip(HEADERS, row + [""] * (len(HEADERS) - len(row))))
            ts = datetime.strptime(row_dict["Timestamp"], "%Y-%m-%d %H:%M:%S")
            if ts >= cutoff:
                visitors.append(row_dict)
        except Exception:
            continue
    return visitors


def get_total_count(all_rows):
    return max(0, len(all_rows) - 1)


# ─── Build the spoken script ───────────────────────────────────────────────────

def build_voice_script(today_str, day_of_week, recent, hot_leads, total):
    """Build a natural-sounding spoken script for the morning voice report."""

    lines = []

    # Greeting
    lines.append(f"Good morning, Austin!")
    lines.append(f"This is your MrCeesAI daily briefing for {today_str}.")
    lines.append("")

    # BNI Overnight Summary
    lines.append("BNI Overnight Summary.")
    if len(recent) == 0:
        lines.append("No new BNI visitors in the last 24 hours.")
        lines.append("Remember to share your form link at your next meeting to keep the pipeline full.")
    elif len(recent) == 1:
        lines.append("You had 1 new BNI visitor overnight.")
    else:
        lines.append(f"You had {len(recent)} new BNI visitors overnight.")

    if hot_leads:
        lines.append(f"You have {len(hot_leads)} hot lead{'s' if len(hot_leads) > 1 else ''} that need your attention today.")
        for v in hot_leads:
            fn = v.get("First Name", "")
            ln = v.get("Last Name", "")
            biz = v.get("Business Name", "")
            lvl = v.get("Interest Level", "")
            lines.append(f"{fn} {ln} from {biz} said they are {lvl}. Follow up with them within the hour.")
    else:
        lines.append("No hot leads overnight. Keep building that pipeline!")

    lines.append(f"Your total all-time BNI visitor count is now {total}.")
    lines.append("")

    # Today's focus based on day of week
    lines.append("Today's focus.")
    lines.append(WEEKLY_TASKS.get(day_of_week, "Stay focused and keep executing!"))
    lines.append("")

    # Daily task checklist
    lines.append("Here are your daily tasks to knock out today.")
    for i, task in enumerate(DAILY_TASKS, 1):
        lines.append(f"Task {i}. {task}")
    lines.append("")

    # Closing
    lines.append("That is your full briefing for today, Austin.")
    lines.append("You are building something great. Stay consistent, stay focused, and let's get it!")
    lines.append("MrCeesAI — powered by Austin Jones.")

    return " ".join(lines)


# ─── Build the text message (HTML for Telegram) ───────────────────────────────

def build_text_message(today_str, day_of_week, recent, hot_leads, total):
    msg = f"<b>Good morning, Austin!</b> \U0001f31e\n"
    msg += f"<b>MrCeesAI Daily Briefing</b> — {today_str}\n"
    msg += "\u2500" * 20 + "\n\n"

    msg += f"<b>\U0001f465 BNI Overnight:</b> {len(recent)} new visitor(s)\n"
    msg += f"<b>\U0001f525 Hot Leads:</b> {len(hot_leads)}\n"
    msg += f"<b>\U0001f4ca All-Time Visitors:</b> {total}\n\n"

    if hot_leads:
        msg += "<b>\U0001f6a8 FOLLOW UP NOW:</b>\n"
        for v in hot_leads:
            fn = v.get("First Name", "")
            ln = v.get("Last Name", "")
            biz = v.get("Business Name", "")
            lvl = v.get("Interest Level", "")
            eml = v.get("Email", "")
            ph = v.get("Phone", "N/A")
            msg += f"  • <b>{fn} {ln}</b> | {biz}\n"
            msg += f"    {lvl} | {eml} | {ph}\n"
        msg += "\n"

    msg += f"<b>\U0001f4c5 Today's Focus:</b>\n{WEEKLY_TASKS.get(day_of_week, '')}\n\n"

    msg += "<b>\U0001f4cb Daily Checklist:</b>\n"
    for i, task in enumerate(DAILY_TASKS, 1):
        msg += f"  {i}. {task}\n"

    msg += "\n<b>Let's get it, Austin! \U0001f4aa\U0001f3fe</b>"
    return msg


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    now = datetime.now()
    today_str = now.strftime("%A, %B %d, %Y")
    day_of_week = now.weekday()  # 0=Monday, 6=Sunday

    # Load BNI data
    try:
        all_rows = get_sheet_data()
        recent = get_recent_visitors(all_rows, days=1)
        total = get_total_count(all_rows)
    except Exception as e:
        send_telegram_text(f"<b>MrCeesAI Morning Report</b>\nCould not load BNI data: {e}")
        exit(1)

    hot_leads = [v for v in recent if v.get("Interest Level") in ["Ready to apply!", "Very interested"]]

    # ── 1. Send the text summary ──────────────────────────────────────────────
    text_msg = build_text_message(today_str, day_of_week, recent, hot_leads, total)
    send_telegram_text(text_msg)
    print("Text report sent to Telegram.")

    # ── 2. Generate & send the voice message ─────────────────────────────────
    try:
        voice_script = build_voice_script(today_str, day_of_week, recent, hot_leads, total)

        # Generate MP3 using gTTS (free, no API key)
        tts = gTTS(text=voice_script, lang="en", slow=False)

        # Save to a temp file and send as Telegram voice note
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        # gTTS saves as mp3 internally; Telegram accepts .ogg for voice
        # Save as .ogg (Telegram voice) — gTTS can write to any path
        tts.save(tmp_path)
        send_telegram_voice(tmp_path)
        os.unlink(tmp_path)  # Clean up temp file
        print("Voice report sent to Telegram.")

    except Exception as e:
        # Voice failed — text already sent, so just log it
        print(f"Voice send failed (text was sent successfully): {e}")
        send_telegram_text(f"<i>Note: Voice message could not be generated today. ({e})</i>")

    print(f"Morning briefing complete — {len(recent)} visitors, {len(hot_leads)} hot leads.")
