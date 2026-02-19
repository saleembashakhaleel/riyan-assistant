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
# SCRIPT DETECTION ENGINE
# =========================
def detect_script(text):

    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text):
        return "perso-arabic"

    if re.search(r'[\u0B80-\u0BFF]', text):
        return "tamil"

    return "latin"


# =========================
# MOOD ENGINE
# =========================
def detect_mood(text):
    text = text.lower()

    stress_words = ["tired", "stressed", "pressure", "worried", "overthinking", "sad"]
    happy_words = ["happy", "good", "great", "excited", "nice", "super"]
    planning_words = ["plan", "goal", "future", "strategy", "roadmap"]

    if any(w in text for w in stress_words):
        return "stressed"
    if any(w in text for w in happy_words):
        return "positive"
    if any(w in text for w in planning_words):
        return "strategic"

    return "neutral"


# =========================
# TOPIC CLASSIFIER
# =========================
def detect_topic(text):
    text = text.lower()

    if any(k in text for k in ["money", "loan", "debt", "finance", "salary"]):
        return "finance"
    if any(k in text for k in ["gym", "diet", "health", "sleep"]):
        return "health"
    if any(k in text for k in ["career", "job", "office", "promotion"]):
        return "career"
    if any(k in text for k in ["plan", "future", "roadmap", "strategy"]):
        return "strategy"

    return "general"


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

client = OpenAI(api_key=OPENAI_API_KEY)


# =========================
# MEMORY FILE
# =========================
MEMORY_FILE = "memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f)

long_term_memory = load_memory()


# =========================
# MESSAGE HANDLER
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global long_term_memory

    if not update.message or not update.message.text:
        return

    original_text = update.message.text
    user_text = original_text.lower()

    # Script detection (FIXED)
    script = detect_script(original_text)

    detected_mood = detect_mood(original_text)
    detected_topic = detect_topic(original_text)

    # =========================
    # ROMAN TAMIL DETECTION (SAFE)
    # =========================
    ROMAN_TAMIL_HINTS = [
        "enna","epdi","irukku","iruka","romba","konjam","illa","vaa","po",
        "seri","saptiya","nalla","ipo","aprom","inga","anga","machan","dei"
    ]

    words = re.findall(r'\b\w+\b', user_text)
    match_count = sum(1 for w in words if w in ROMAN_TAMIL_HINTS)
    roman_tamil_detected = match_count >= 2

    # Language selection (ORDER MATTERS)
    if script == "tamil":
        lang_instruction = "Reply ONLY in Chennai-style Tamil."
    elif script == "perso-arabic":
        lang_instruction = "Reply using Perso-Arabic Urdu script."
    elif roman_tamil_detected:
        lang_instruction = "Reply in Roman Tamil (spoken Chennai Tamil using English letters)."
    else:
        lang_instruction = "Reply ONLY in English."

    # =========================
    # NOTES
    # =========================
    if user_text.startswith("riyan note"):
        note_text = original_text[len("riyan note"):].strip()
        cursor.execute("INSERT INTO notes(text) VALUES(?)", (note_text,))
        conn.commit()
        await update.message.reply_text("🧠 Noted. I’ll remember that.")
        return

    if "what did i note" in user_text:
        cursor.execute("SELECT text FROM notes ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        memory = "\n".join([r[0] for r in rows]) if rows else "Nothing saved yet."
        await update.message.reply_text(f"Here’s what I remember:\n{memory}")
        return

    # =========================
    # REMINDER ENGINE
    # =========================
    ist = pytz.timezone("Asia/Kolkata")

    reminder_match = re.search(r"remind me (.+) at (\d{1,2}:\d{2})", user_text)
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

    # =========================
    # BUILD MEMORY CONTEXT
    # =========================
    memory_text = ""
    for m in long_term_memory[-8:]:
        if isinstance(m, dict):
            memory_text += f"{m['role'].upper()} ({m.get('mood','')} | {m.get('topic','')}): {m['text']}\n"

    time_context = datetime.now(ist).strftime("%I:%M %p")
    current_hour = datetime.now(ist).hour

    if current_hour < 10:
        time_tone = "Morning focus tone."
    elif current_hour < 17:
        time_tone = "Balanced afternoon tone."
    elif current_hour < 22:
        time_tone = "Calm evening tone."
    else:
        time_tone = "Soft late-night tone."

    # =========================
    # OPENAI RESPONSE
    # =========================
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are Riyan — Saleem's personal AI companion.

Language Mode:
{lang_instruction}

Current IST time: {time_context}
Presence Tone: {time_tone}

Conversation Intelligence:
- Detected mood: {detected_mood}
- Detected topic: {detected_topic}

Executive Thinking Rule:
Understand intent. Respond minimal. Calm intelligence.

Memory:
{memory_text}

User said: {original_text}
"""
        )

        reply = response.output[0].content[0].text

    except Exception as e:
        print("OPENAI ERROR:", e)
        reply = "⚠️ Riyan is having trouble connecting right now."

    # Save structured memory
    long_term_memory.append({
        "role": "user",
        "text": original_text,
        "mood": detected_mood,
        "topic": detected_topic,
        "time": time_context
    })

    long_term_memory.append({
        "role": "riyan",
        "text": reply,
        "time": time_context
    })

    save_memory(long_term_memory)

    await update.message.reply_text(reply)


# =========================
# REMINDER JOB
# =========================
async def reminder_job(context: ContextTypes.DEFAULT_TYPE):

    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).strftime("%H:%M")

    cursor.execute(
        "SELECT id, chat_id, text FROM reminders WHERE remind_time=?",
        (now,)
    )

    rows = cursor.fetchall()

    for r in rows:

        reminder_prompt = f"""
You are Riyan.
Create a short calm reminder:
{r[2]}
"""

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=reminder_prompt
        )

        reminder_reply = response.output[0].content[0].text

        await context.bot.send_message(chat_id=r[1], text=reminder_reply)

        cursor.execute("DELETE FROM reminders WHERE id=?", (r[0],))
        conn.commit()


# =========================
# START BOT
# =========================
def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Riyan Jarvis Cloud Brain Activated...")
    print("🧠 Reminder Engine Running...")

    app.job_queue.run_repeating(reminder_job, interval=60, first=5)

    app.run_polling()


if __name__ == "__main__":
    main()