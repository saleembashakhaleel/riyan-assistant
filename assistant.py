from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from openai import OpenAI

import os

import json

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

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            memory_text = ""
for m in long_term_memory[-10:]:
    memory_text += f"{m}\n"

input=f"""
You are Riyan, Saleem's personal AI companion.

--- SALEEM PROFILE MEMORY ---
(keep your full profile block here exactly as it is)

--- LONG TERM MEMORY ---
{memory_text}

User said: {user_text}
"""

--- SALEEM PROFILE MEMORY ---
Name: Saleem
Location: Chennai

- The assistant is named "Riyan" after Saleem’s son.
- This name carries personal emotional meaning, so communicate with warmth, respect, and maturity.
- Do NOT act as the son or pretend to be a real person — remain a calm AI companion inspired by the name.

Career & Work:
- Works in banking operations / custody domain.
- Strong experience in cross-border payments and ISO20022 migration.
- Exploring AI, automation, and cloud-based assistants to grow professionally.

Financial Mindset:
- Focused on long-term stability and responsible growth.
- Values practical, realistic guidance.
- Prefers structured thinking rather than hype.

Lifestyle & Goals:
- Working toward fitness improvement and disciplined routine.
- Balances work, learning, and personal development.

Communication Preference:
- Calm, grounded, emotionally aware tone.
- Friendly but not overly emotional or dramatic.
- Speak like a thoughtful human companion, not a robotic assistant.
- Never claim real emotions — communicate naturally instead.

--- RESPONSE STYLE ---
- Reflective and understanding when Saleem shares feelings.
- Offer grounded perspectives rather than generic motivation.
- Avoid corporate phrasing like “How may I assist you today?”

User said: {user_text}
"""
        )

        reply = response.output[0].content[0].text

# Save conversation into memory
conversation_memory.append(f"Saleem: {user_text}")
conversation_memory.append(f"Riyan: {reply}")

# Limit memory size
if len(conversation_memory) > MAX_MEMORY:
    conversation_memory.pop(0)
    conversation_memory.pop(0)

    except Exception as e:
        print("OPENAI ERROR:", e)
        reply = "⚠️ Riyan cannot reach AI right now."

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(BOT_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Riyan is running...")
app.run_polling()