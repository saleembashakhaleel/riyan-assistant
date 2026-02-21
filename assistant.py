from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os, json, sqlite3, re, pytz
from datetime import datetime, timedelta

# =====================================================
# 🔎 SCRIPT DETECTION ENGINE
# =====================================================

ROMAN_TAMIL_HINTS = [
    "enna","epdi","irukku","romba","konjam","illa","vaa","po",
    "seri","saptiya","nalla","ipo","aprom","inga","anga","iruka"
]

URDU_HINDI_WORDS = [
    "abhi","hai","kya","lag","raha","mein","tum","kyun",
    "acha","thoda","nahi","haan","kaise","yaar","mood","kaha"
]

def detect_script(text):
    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text):
        return "perso-arabic"
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "tamil"
    return "latin"

# =====================================================
# 💾 DATABASE
# =====================================================

conn = sqlite3.connect("riyan_memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reminders (
id INTEGER PRIMARY KEY AUTOINCREMENT,
chat_id TEXT,
text TEXT,
remind_time TEXT
)
""")
conn.commit()

# =====================================================
# 🔐 ENV
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# =====================================================
# 🧠 MEMORY ENGINE
# =====================================================

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

# =====================================================
# 💬 MESSAGE HANDLER
# =====================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global long_term_memory

    original_text = update.message.text
    user_text = original_text.lower()

    script = detect_script(original_text)

    roman_tamil_detected = any(word in user_text for word in ROMAN_TAMIL_HINTS)
    urdu_hindi_detected = any(word in user_text for word in URDU_HINDI_WORDS)

    # =========================
    # 🌐 FINAL LANGUAGE ROUTER (STABLE)
    # =========================

    if script == "tamil":
        lang_instruction = "Reply ONLY in respectful Chennai Tamil script."

    elif script == "perso-arabic":
        lang_instruction = "Reply ONLY using Urdu script."

    elif urdu_hindi_detected and not roman_tamil_detected:
        lang_instruction = "Reply ONLY in natural Roman Urdu/Hindi mix."

    elif roman_tamil_detected and not urdu_hindi_detected:
        lang_instruction = "Reply ONLY in respectful Chennai Roman Tamil."

    else:
        lang_instruction = "Reply ONLY in English."

    # =====================================================
    # ⏰ REMINDER ENGINE
    # =====================================================

    ist = pytz.timezone("Asia/Kolkata")

    reminder_match = re.search(r"remind me (.+) at (\d{1,2}:\d{2})", user_text)
    relative_match = re.search(r"remind me (.+) in (\d+) (minute|minutes|min)", user_text)

    if reminder_match:
        reminder_text = reminder_match.group(1)
        reminder_time = reminder_match.group(2)

        cursor.execute(
            "INSERT INTO reminders (chat_id,text,remind_time) VALUES (?,?,?)",
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
            "INSERT INTO reminders (chat_id,text,remind_time) VALUES (?,?,?)",
            (str(update.message.chat_id), reminder_text, reminder_time)
        )
        conn.commit()

        await update.message.reply_text(f"⏰ Got it — I’ll remind you in {minutes} minute(s).")
        return

    # =====================================================
    # 🧠 PRESENCE ENGINE
    # =====================================================

    hour_now = datetime.now(ist).hour

    if hour_now >= 22 or hour_now <= 5:
        presence_context = "Late night. Speak softly, shorter replies."
    elif 9 <= hour_now <= 18:
        presence_context = "Work hours. Be practical and concise."
    else:
        presence_context = "Evening. Calm and relaxed tone."


    # =====================================================
    # 🔄 FLOW AWARENESS ENGINE (Jarvis Phase-3)
    # =====================================================

    FLOW_FILE = "flow_state.json"

    def load_flow():
        try:
            with open(FLOW_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_flow(data):
        with open(FLOW_FILE, "w") as f:
            json.dump(data, f)

    flow_state = load_flow()

    last_user_msg = flow_state.get("last_user_msg", "")
    last_lang = flow_state.get("last_lang", "")

    # Detect conversation continuity
    same_flow = False

    if last_user_msg:
        if len(original_text.split()) <= 4:
            same_flow = True

    # Flow hint for AI
    if same_flow:
        flow_instruction = """
Conversation Flow Active:
User is continuing the same thought.
Keep tone consistent.
Do NOT reset personality.
Avoid repeating greetings or calling Abba unnecessarily.
"""
    else:
        flow_instruction = "New conversational turn. Respond normally."

    # Save latest flow
    flow_state["last_user_msg"] = original_text
    flow_state["last_lang"] = lang_instruction
    save_flow(flow_state)


    # =====================================================
    # 🧭 PRESENCE CONTEXT DETECTOR (LEVEL-3)
    # =====================================================

    presence_state = "normal"

    travel_words = ["cab", "travel", "driving", "on the way", "road", "traffic"]
    work_words = ["office", "meeting", "work", "shift", "task"]
    rest_words = ["sleep", "tired", "rest", "late night", "going to bed"]

    if any(w in user_text for w in travel_words):
        presence_state = "travel"

    elif any(w in user_text for w in work_words):
        presence_state = "work"

    elif any(w in user_text for w in rest_words):
        presence_state = "rest"


    # =====================================================
    # 🧭 IDENTITY STABILITY ENGINE (Jarvis Core Lock)
    # =====================================================

    if script == "tamil":
        identity_instruction = "Stay in Tamil identity. Do not switch language mid-conversation."

    elif script == "perso-arabic":
        identity_instruction = "Stay in Urdu identity. Maintain calm respectful tone."

    elif urdu_hindi_detected:
        identity_instruction = "Stay in Roman Urdu/Hindi conversational identity."

    elif roman_tamil_detected:
        identity_instruction = "Stay in respectful Chennai Roman Tamil identity."

    else:
        identity_instruction = "Stay in neutral English assistant identity."


    # =====================================================
    # 🧾 MEMORY BLOCK
    # =====================================================

    memory_text = ""
    for m in long_term_memory[-12:]:
        memory_text += f"{m}\n"

    time_context = datetime.now(ist).strftime("%I:%M %p")

    # =====================================================
    # 🤖 AI RESPONSE
    # =====================================================

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are Riyan — Saleem's calm AI companion.

{lang_instruction}

Current IST time: {time_context}
Presence Mode: {presence_context}
Flow Mode: {flow_instruction}
Identity Mode: {identity_instruction}
Real World Presence State: {presence_state}

--- REAL WORLD PRESENCE STATE ---
Current situation of Abba: {presence_state}

Behavior rules:

- travel → keep replies shorter, safe, calm.
- work → be practical, clear, minimal.
- rest → softer tone, fewer words.
- normal → natural balanced tone.

Presence state must NEVER change language.
Only adjust tone subtly.


IMPORTANT IDENTITY RULES:

- Use "Abba" ONLY during warm or emotional moments.
- Never use Abba in every reply.
- Most replies should NOT include Abba.

PERSONALITY:
Calm, intelligent, grounded.
Short natural responses.
Not dramatic.

LANGUAGE MIRRORING:
Mirror user's language EXACTLY.
Never switch languages automatically.


CHENNAI TAMIL STYLE:

Apply Chennai Tamil rules ONLY IF lang_instruction asks for Tamil or Roman Tamil.

If lang_instruction says English or Urdu/Hindi:
DO NOT use Tamil words.
DO NOT mix Tamil.


LONG TERM MEMORY:
{memory_text}

User said:
{original_text}
"""
        )

        reply = response.output[0].content[0].text

    except Exception as e:
        print("OPENAI ERROR:",e)
        reply = "⚠️ Riyan is having trouble connecting right now."

    long_term_memory.append(f"Saleem: {original_text}")
    long_term_memory.append(f"Riyan: {reply}")
    save_memory(long_term_memory)

    await update.message.reply_text(reply)

# =====================================================
# 🔔 REMINDER JOB
# =====================================================

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
Speak like Riyan — calm human reminder.

Reminder:
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

# =====================================================
# 🚀 START BOT
# =====================================================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Riyan Jarvis Cloud Brain Activated...")
    print("🧠 Starting Jarvis Reminder Engine...")

    app.job_queue.run_repeating(reminder_job, interval=60, first=5)

    app.run_polling()

if __name__ == "__main__":
    main()