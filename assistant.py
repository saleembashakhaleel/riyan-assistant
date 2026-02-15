from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os
import json
import sqlite3
import re
import pytz
from datetime import datetime, timedelta

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("riyan_memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT,
    text TEXT,
    remind_time TEXT
)
""")
conn.commit()

# =========================
# ENV
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")

WEBHOOK_URL = f"https://{RAILWAY_PUBLIC_DOMAIN}/{BOT_TOKEN}"

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# MEMORY
# =========================

MEMORY_FILE = "memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE,"r") as f:
            return json.load(f)
    except:
        return []

def save_memory(data):
    with open(MEMORY_FILE,"w") as f:
        json.dump(data,f)

long_term_memory = load_memory()

# =========================
# MESSAGE HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global long_term_memory

    user_text = update.message.text.lower()

    # -------- SAVE NOTES --------
    if user_text.startswith("riyan note"):
        note_text = update.message.text[len("riyan note"):].strip()
        cursor.execute("INSERT INTO notes(text) VALUES(?)",(note_text,))
        conn.commit()
        await update.message.reply_text("🧠 Noted. I’ll remember that.")
        return

    if "what did i note" in user_text:
        cursor.execute("SELECT text FROM notes ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        memory = "\n".join([r[0] for r in rows]) if rows else "Nothing saved yet."
        await update.message.reply_text(f"Here’s what I remember:\n{memory}")
        return
 
    # --- JARVIS REMINDER INTENT ---

    import re
    import pytz
    from datetime import datetime, timedelta

    ist = pytz.timezone("Asia/Kolkata")

    # 1️⃣ EXACT TIME (existing behavior)
    reminder_match = re.search(r"remind me (.+) at (\d{1,2}:\d{2})", user_text)

    # 2️⃣ RELATIVE TIME (NEW)
    relative_match = re.search(r"remind me (.+) in (\d+) (minute|minutes|min)", user_text)

    if reminder_match:

        reminder_text = reminder_match.group(1)
        reminder_time = reminder_match.group(2)

    cursor.execute(
        "INSERT INTO reminders (chat_id, text, remind_time) VALUES (?,?,?)",
        (str(update.message.chat_id), reminder_text, reminder_time)
    )
    conn.commit()

    await update.message.reply_text(f"⏰ Reminder set for {reminder_time}")
    return


    if relative_match:

    reminder_text = relative_match.group(1)
    minutes = int(relative_match.group(2))

    future_time = datetime.now(ist) + timedelta(minutes=minutes)
    reminder_time = future_time.strftime("%H:%M")

    cursor.execute(
        "INSERT INTO reminders (chat_id, text, remind_time) VALUES (?,?,?)",
        (str(update.message.chat_id), reminder_text, reminder_time)
    )
    conn.commit()

    await update.message.reply_text(f"⏰ Got it — I’ll remind you in {minutes} minute(s).")
    return


    # -------- AI RESPONSE --------
    memory_text = ""
    for m in long_term_memory[-12:]:
        memory_text += f"{m}\n"

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are Riyan, Saleem's personal AI companion.

--- SALEEM PROFILE MEMORY ---
Name: Saleem
Location: Chennai
Assistant name inspired by his son Riyan.

Career:
- Banking custody & cross-border payments
- ISO20022 migration experience
- Exploring AI automation

Communication Style:
- Calm
- Grounded
- Human-like but not dramatic
- Short natural responses (2–3 sentences)
- Reflect first, advise second

--- LONG TERM MEMORY ---
{memory_text}

User said: {user_text}
"""
        )

        reply = response.output[0].content[0].text

    except Exception as e:
        print("OPENAI ERROR:",e)
        reply = "⚠️ Riyan is having trouble connecting right now."

    long_term_memory.append(f"Saleem: {user_text}")
    long_term_memory.append(f"Riyan: {reply}")
    save_memory(long_term_memory)

    await update.message.reply_text(reply)

# =========================
# JARVIS REMINDER JOB (FIXED)
# =========================
from datetime import datetime

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):

    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).strftime("%H:%M")

    print("CURRENT IST TIME:", now)

    cursor.execute(
        "SELECT id, chat_id, text FROM reminders WHERE remind_time=?",
        (now,)
    )

    rows = cursor.fetchall()

    for r in rows:

        reminder_prompt = f"""
You are Riyan, Saleem's personal AI companion.
Speak naturally, calmly, and warmly.
Keep it short and human, not robotic.

Create a gentle reminder message for:
{r[2]}
"""

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=reminder_prompt
        )

        reminder_reply = response.output[0].content[0].text

        await context.bot.send_message(
            chat_id=r[1],
            text=reminder_reply
        )

        cursor.execute("DELETE FROM reminders WHERE id=?", (r[0],))
        conn.commit()
# ========================
# START JARVIS CLOUD BRAIN
# ========================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Riyan Jarvis Cloud Brain Activated...")
    print("🧠 Starting Jarvis Reminder Engine...")

    app.job_queue.run_repeating(
        reminder_job,
        interval=60,
        first=10
    )

    app.run_polling()

if __name__ == "__main__":
    main()