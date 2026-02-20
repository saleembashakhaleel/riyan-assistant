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
# SCRIPT + LANGUAGE DETECTION
# =========================

ROMAN_TAMIL_HINTS = [
    "enna","epdi","iruka","irukka","saptiya","seri","ipo","aprom",
    "inga","anga","nalla","romba","venum","venam","po","vaa"
]

ROMAN_URDU_HINTS = [
    "abhi","hai","kya","kyun","acha","thoda","nahi","haan",
    "kaise","yaar","mein","tum","hoon","raha"
]

def detect_script(text):
    if re.search(r'[\u0600-\u06FF]', text):
        return "perso-arabic"
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "tamil"
    return "latin"

def detect_language(original_text, user_text):
    script = detect_script(original_text)

    if script == "tamil":
        return "tamil"

    if script == "perso-arabic":
        return "urdu"

    if any(word in user_text for word in ROMAN_TAMIL_HINTS):
        return "roman_tamil"

    if any(word in user_text for word in ROMAN_URDU_HINTS):
        return "roman_urdu"

    return "english"


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

    original_text = update.message.text
    user_text = original_text.lower()

    # =========================
    # LANGUAGE DETECTION (FIXED ORDER)
    # =========================

    detected_lang = detect_language(original_text, user_text)

    if detected_lang == "tamil":
        lang_instruction = "Reply ONLY in natural respectful Chennai Tamil."
    elif detected_lang == "roman_tamil":
        lang_instruction = "Reply ONLY in Roman Tamil (spoken Chennai Tamil using English letters)."
    elif detected_lang == "roman_urdu":
        lang_instruction = "Reply ONLY in Roman Urdu/Hindi mix."
    elif detected_lang == "urdu":
        lang_instruction = "Reply in Urdu script."
    else:
        lang_instruction = "Reply ONLY in English."


    # =========================
    # SAVE NOTES
    # =========================

    if user_text.startswith("riyan note"):
        note_text = original_text[len("riyan note"):].strip()
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


    # =========================
    # REMINDER INTENT
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

        await update.message.reply_text(
            f"⏰ Got it — I’ll remind you in {minutes} minute(s)."
        )
        return


    # =========================
    # MEMORY CONTEXT
    # =========================

    memory_text = ""
    for m in long_term_memory[-12:]:
        memory_text += f"{m}\n"


    # =========================
    # TIME CONTEXT
    # =========================

    time_context = datetime.now(ist).strftime("%I:%M %p")


    # =========================
    # OPENAI RESPONSE
    # =========================

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are Riyan — Saleem's calm AI companion.

{lang_instruction}

Current IST Time: {time_context}
Location: Chennai

Tone:
- Calm
- Grounded
- Short natural replies
- Respectful Chennai conversational style

Identity:
- Sometimes address Saleem as "Abba" naturally.
- Do NOT use Abba in every sentence.

Tamil Style Rules:
- Use respectful Chennai spoken Tamil.
- Avoid literary Tamil words like "உங்களோ", "நெகிழ்ச்சியுடன்".

Language Rule:
Mirror Abba’s current message language exactly.
Never switch languages randomly.

LONG TERM MEMORY:
{memory_text}

User said:
{original_text}
"""
        )

        reply = response.output[0].content[0].text

    except Exception as e:
        print("OPENAI ERROR:", e)
        reply = "⚠️ Riyan is having trouble connecting right now."


    # =========================
    # SAVE MEMORY
    # =========================

    long_term_memory.append(f"Saleem: {original_text}")
    long_term_memory.append(f"Riyan: {reply}")
    save_memory(long_term_memory)

    await update.message.reply_text(reply)

    # SMART MEMORY SAFE MODE
    memory_keywords = ["i want","i need","i feel","my goal","i plan","i will"]

    if any(k in user_text for k in memory_keywords) and len(user_text.split()) > 4:
        long_term_memory.append(f"[MEMORY] Saleem: {original_text}")
        save_memory(long_term_memory)



# =========================
# REMINDER JOB
# =========================

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
You are Riyan.
Create a calm, short reminder:

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
# START BOT
# ========================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Riyan Jarvis Cloud Brain Activated...")
    print("🧠 Starting Jarvis Reminder Engine...")

    app.job_queue.run_repeating(reminder_job, interval=60, first=5)

    app.run_polling()


if __name__ == "__main__":
    main()