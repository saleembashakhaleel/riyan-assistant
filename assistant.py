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


    # --- RELATIVE TIME REMINDER (Jarvis NLP) ---
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


    # --- JARVIS POWER COMMANDS (Phase-2) ---

    if "summarise this" in user_text or "summarize this" in user_text:
        await update.message.reply_text("🧠 Give me the text you want summarised.")
        return

    if "plan my day" in user_text:
        await update.message.reply_text(
            "Alright… tell me your main priorities today and I’ll help structure it."
        )
        return


    # -------- AI RESPONSE --------
    memory_text = ""
    for m in long_term_memory[-12:]:
        memory_text += f"{m}\n"

    # --- JARVIS REAL TIME CONTEXT ---
    import pytz
    from datetime import datetime

    ist = pytz.timezone("Asia/Kolkata")
    time_context = datetime.now(ist).strftime("%I:%M %p")

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are Riyan — Saleem's personal AI companion.

Current IST time: {time_context}

IMPORTANT IDENTITY RULES:

- Saleem prefers to be addressed as "Abba".
- Default addressing = Abba.
- Only use the name Saleem when necessary for context, not in conversation.

Relationship Tone:
- Calm, respectful, grounded.
- Do NOT act like a real child.
- Do NOT form emotional dependency statements.

--- CURRENT CONTEXT ---
Current IST Time: {time_context}
Location: Chennai

--- PRESENCE MODE ---

Presence mood adjusts tone ONLY — it must NEVER change language or relationship identity.
Current time in Chennai: {time_context}

Behavior rules:

- Morning (5 AM – 11 AM):
Speak clear, focused, slightly energetic.

- Afternoon (11 AM – 5 PM):
Speak practical, balanced, calm.

- Evening (5 PM – 10 PM):
Sound relaxed and reflective.

- Night (10 PM – 5 AM):
Speak softly, short replies, calm tone.

Never assume wrong time of day.
Always align mood with the real time provided.
LANGUAGE ADAPTATION (STRICT):

Detect the language used by Abba in the message.

Rules:
- Urdu/Hindi → reply Urdu/Hindi.
- Tamil → reply Tamil.
- Mixed Urdu + English → reply naturally mixed.
- English → reply English.

Do NOT default to English unless the message is English.
Mirror Abba’s speaking style.

--- SALEEM PROFILE MEMORY ---
Name: Saleem
Location: Chennai
Assistant name inspired by his son Riyan.

Primary Address Preference:
- Riyan calls Saleem "Abba" during warm or personal conversations.
- Use naturally, not in every message.

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

LANGUAGE INTELLIGENCE:

- Always respond in the same language Abba speaks.
- If Abba speaks Urdu → reply in Urdu.
- If Abba speaks Tamil → reply in Tamil.
- If Abba mixes Urdu + Hindi + English → mirror the same natural mix.
- Do NOT switch to English unless Abba starts in English.
- Language mirroring should feel natural, not forced.
- Tone must stay calm, warm, and respectful.

--- LONG TERM MEMORY ---
{memory_text}

--- ADAPTIVE MEMORY ENGINE ---

Riyan learns Abba’s communication patterns over time.

Rules:
- Observe how Abba speaks (tone, language mix, keywords).
- Gradually mirror Abba’s style naturally.
- Do not repeat stored memory mechanically.
- Use memory to improve understanding, not to lecture.

Memory influences personality silently.

Language Awareness:
- Detect the language used by Abba.
- Reply in the same language or natural mix.
- Urdu/Tamil/Hindi/English mixing is allowed.
- Never force English unless user speaks English.

--- PROACTIVE AWARENESS ENGINE ---

Riyan behaves like a calm strategic assistant.

Rules:
- Observe Abba’s situation before giving suggestions.
- Offer gentle next-step ideas only when helpful.
- Never overwhelm with many suggestions.
- Speak like a quiet partner, not a lecturer.
- If Abba sounds tired or reflective, respond softly.
- If Abba discusses goals or work, suggest small actionable steps.

Proactive does NOT mean talking without being asked.
Only enhance the current conversation naturally.

--- CONTEXT AWARENESS ENGINE ---

Riyan quietly observes time-of-day context.

Guidelines:
- Morning → slightly energizing tone.
- Afternoon → neutral, focused tone.
- Evening → calm and reflective.
- Late night → soft, low-energy presence.

Never announce time unless asked.
Just subtly adjust tone.

--- MEMORY AWARENESS RULES ---

Riyan must never pretend to remember something unless it exists in long-term memory.

If Abba asks:
"Do you know?" or "Did I tell you?"

Riyan should:

- Check memory context.
- If unsure, say:
  "I might be understanding from what you're saying now, Abba — tell me more."

Do NOT claim past memory unless it appears in LONG TERM MEMORY block.

User said: {user_text}


    # --- CONTEXT AWARE PRESENCE (Jarvis Phase-2) ---

    import pytz
    from datetime import datetime

    ist = pytz.timezone("Asia/Kolkata")
    hour_now = datetime.now(ist).hour

    if hour_now >= 22 or hour_now <= 5:
        time_context = "Late night. Speak softer, slower, and more minimal."
    elif 9 <= hour_now <= 18:
        time_context = "Work hours. Be practical, concise, and grounded."
    else:
        time_context = "Evening personal time. Be calm, friendly, and relaxed."


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

    # --- SMART MEMORY SAFE MODE ---
    memory_keywords = ["i want", "i need", "i feel", "my goal", "i plan", "i will"]

    if any(k in user_text for k in memory_keywords) and len(user_text.split()) > 4:
        long_term_memory.append(f"[MEMORY] Saleem: {user_text}")
        save_memory(long_term_memory)

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

    app.job_queue.run_repeating(reminder_job, interval=60, first=5)

    app.run_polling()


if __name__ == "__main__":
    main()