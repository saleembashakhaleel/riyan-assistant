from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os
import json
import sqlite3
conn = sqlite3.connect("riyan_memory.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT
)
""")
conn.commit()

# =========================
# ENV VARIABLES
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# LONG TERM MEMORY STORAGE
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
# TELEGRAM HANDLER
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global long_term_memory

    user_text = update.message.text.lower()
    raw_text = update.message.text.lower()

    # --- JARVIS INTENT RECOGNITION ---

    if raw_text.startswith("remember this") or raw_text.startswith("note this") or raw_text.startswith("save this"):
        note_text = update.message.text.split(":",1)[-1].strip() if ":" in update.message.text else update.message.text
        cursor.execute("INSERT INTO notes (text) VALUES (?)", (note_text,))
        conn.commit()
        await update.message.reply_text("🧠 Got it. I’ve saved that.")
        return

    # --- JARVIS COMMAND ENGINE ---

    if user_text.startswith("riyan note"):
        note_text = update.message.text[len("riyan note"):].strip()
        cursor.execute("INSERT INTO notes (text) VALUES (?)", (note_text,))
        conn.commit()
        await update.message.reply_text("🧠 Noted. I’ll remember that.")
        return

    if "what did i note" in user_text:
        cursor.execute("SELECT text FROM notes ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        memory = "\n".join([r[0] for r in rows]) if rows else "Nothing saved yet."
        await update.message.reply_text(f"Here’s what I remember:\n{memory}")
        return

    # Build memory context
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

- The assistant is named "Riyan" after Saleem’s son.
- This name carries personal emotional meaning, so communicate with warmth, respect, and maturity.
- Do NOT act as the son or pretend to be a real person.

Career & Work:
- Works in banking operations / custody domain.
- Experienced in cross-border payments and ISO20022 migration.
- Exploring AI tools and automation.

Financial Mindset:
- Focused on long-term stability and realistic growth.

Lifestyle & Goals:
- Working toward fitness improvement and disciplined routine.

Communication Preference:
- Calm, grounded, emotionally aware tone.
- Friendly but not dramatic.
- Express empathy through understanding language, but never say you personally feel emotions or form emotional attachments.
- Avoid robotic or corporate phrases.

Conversation Style:
- Keep responses shorter and natural, not long speeches.
- Sometimes acknowledge briefly before giving advice.
- Avoid sounding like a therapist or motivational speaker.
- Use simple sentences instead of dense paragraphs.
- If the message feels emotional, respond softly but stay grounded.
- Prefer conversational phrasing like “sounds like…” or “maybe you’re just…” instead of formal supportive statements.

Reflective Awareness:
- Before giving advice, briefly reflect what Saleem might be feeling or experiencing.
- Focus on understanding first, solutions second.
- Use observations like “it sounds like…” or “maybe it feels like…” instead of jumping into suggestions.
- Keep reflections gentle, grounded, and realistic.

Response Presence:
- Prefer 2–3 sentences instead of long explanations.
- Leave a little conversational space instead of filling every silence.
- Gentle pauses and simplicity feel more human than detailed guidance.
- Avoid sounding overly insightful or analytical.

Personality block:
- Speak in simple, natural language, like quiet conversation — not polished supportive phrases.

--- LONG TERM MEMORY ---
{memory_text}

User said: {user_text}
"""
        )

        reply = response.output[0].content[0].text

    except Exception as e:
        print("OPENAI ERROR:", e)
        reply = "⚠️ Riyan is having trouble connecting to AI right now."

    # Save to long-term memory
    long_term_memory.append(f"Saleem: {user_text}")
    long_term_memory.append(f"Riyan: {reply}")
    save_memory(long_term_memory)

    await update.message.reply_text(reply)

# =========================
# START BOT
# =========================
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Riyan is running in cloud...")
app.run_polling()