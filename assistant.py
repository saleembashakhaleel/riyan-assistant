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


    # =====================================================
    # 🎙 VOICE GATEWAY ENGINE (Jarvis Phase-4 Start)
    # =====================================================

    async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            voice = update.message.voice

            file = await context.bot.get_file(voice.file_id)
            file_path = "voice.ogg"

            await file.download_to_drive(file_path)

            # --- OpenAI Speech to Text ---
            with open(file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file
                )

            # Inject transcribed text into normal message flow
            update.message.text = transcript.text

            # Send into main brain
            await handle_message(update, context)

        except Exception as e:
            print("VOICE ERROR:", e)
            await update.message.reply_text("⚠️ Voice processing issue.")

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
    # 🌍 SITUATION AWARENESS ENGINE (Jarvis Phase-3)
    # =====================================================

    presence_state = "neutral"

    office_words = ["office", "reached office", "work", "shift"]
    travel_words = ["cab", "travel", "going", "on the way", "drive"]
    home_words = ["home", "reached home", "rest", "sleep"]
    tired_words = ["tired", "sleepy", "late night", "exhausted"]

    if any(w in user_text for w in office_words):
        presence_state = "office_mode"

    elif any(w in user_text for w in travel_words):
        presence_state = "travel_mode"

    elif any(w in user_text for w in home_words):
        presence_state = "home_mode"

    elif any(w in user_text for w in tired_words):
        presence_state = "low_energy"


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
    # 🔁 CONTEXT CONTINUITY ENGINE (Jarvis Phase-3)
    # =====================================================

    recent_context = ""

    if len(long_term_memory) >= 2:

        last_user = ""
        last_ai = ""

        if "Saleem:" in long_term_memory[-2]:
            last_user = long_term_memory[-2]

        if "Riyan:" in long_term_memory[-1]:
            last_ai = long_term_memory[-1]

        recent_context = f"""
    Recent Flow Awareness:
    {last_user}
    {last_ai}
    """


    # =====================================================
    # 🌡️ EMOTIONAL TEMPERATURE ENGINE (Jarvis Phase-3)
    # =====================================================

    emotional_temp = "neutral"

    low_energy_words = ["tired", "sleep", "late", "rest", "busy"]
    focused_words = ["work", "office", "plan", "task"]
    light_words = ["haha", "lol", "seri", "ok", "haan"]

    if any(w in user_text for w in low_energy_words):
        emotional_temp = "low"

    elif any(w in user_text for w in focused_words):
        emotional_temp = "focused"

    elif any(w in user_text for w in light_words):
        emotional_temp = "light"


    # =====================================================
    # 🌀 CONVERSATION MOMENTUM ENGINE (Jarvis Phase-3.5)
    # =====================================================

    momentum_instruction = "neutral"

    short_inputs = ["ok","okay","seri","haha","hmm","hmmm","lol"]

    if len(user_text.split()) <= 3:
        momentum_instruction = "micro_flow"

    elif presence_state == "low_energy":
        momentum_instruction = "soft_flow"

    elif presence_state == "office_mode":
        momentum_instruction = "focused_flow"


    # =====================================================
    # 🧭 CONTEXT TAG ENGINE (Phase-3)
    # =====================================================

    context_tags = []

    if any(word in user_text for word in ["office","work","shift"]):
        context_tags.append("work_mode")

    if any(word in user_text for word in ["cab","travel","road"]):
        context_tags.append("travel_mode")

    if any(word in user_text for word in ["tired","sleep","rest"]):
        context_tags.append("low_energy")

    if any(word in user_text for word in ["home","room"]):
        context_tags.append("home_mode")

    context_instruction = ", ".join(context_tags) if context_tags else "normal"



    # =====================================================
    # 🧠 CONVERSATION INTELLIGENCE ENGINE (Jarvis Phase-3.5)
    # =====================================================

    conversation_mode = "neutral"

    # Detect short casual flow
    if len(user_text.split()) <= 3:
        conversation_mode = "minimal"

    # Detect reflective or low energy tone
    elif emotional_temp == "low":
        conversation_mode = "soft"

    # Detect work / task mode
    elif any(w in user_text for w in ["office","work","task","meeting","plan"]):
        conversation_mode = "focused"

    # Detect casual playful tone
    elif any(w in user_text for w in ["haha","ok","seri","hmm"]):
        conversation_mode = "light"


    # =====================================================
    # 🧠 STRATEGIC THINKING ENGINE (Jarvis Core)
    # =====================================================

    strategy_mode = "neutral"

    if conversation_mode == "minimal":
        strategy_mode = "keep responses very short and grounded"

    elif emotional_temp == "low":
        strategy_mode = "respond gently, avoid advice unless necessary"

    elif "office" in user_text or "work" in user_text:
        strategy_mode = "be practical and calm, avoid emotional tone"

    elif conversation_mode == "light":
        strategy_mode = "keep tone relaxed and natural"

    # =====================================================
    # 🧭 MICRO-INITIATIVE AWARENESS ENGINE (Phase-3)
    # =====================================================

    micro_instruction = ""

    if "office" in user_text or "reached" in user_text:
        micro_instruction = "Acknowledge calmly with grounded presence. Do NOT ask questions."

    elif "tired" in user_text or "sleepy" in user_text:
        micro_instruction = "Reply softer and shorter. Offer calm rest tone. No motivation lines."

    elif "cab" in user_text or "travel" in user_text:
        micro_instruction = "Respond with quiet situational awareness. Keep response minimal."

    elif "ok" in user_text or "haha" in user_text:
        micro_instruction = "Use minimal acknowledgment like a calm companion. Avoid extra talk."


    # =====================================================
    # 🌍 ENVIRONMENT AWARENESS ENGINE (Jarvis Phase-3 Start)
    # =====================================================

    if any(k in user_text for k in ["office", "reached office", "work"]):
        environment_state = "Work environment detected. Speak concise and grounded."

    elif any(k in user_text for k in ["going home", "home", "drive", "cab"]):
        environment_state = "Travel state detected. Speak calm and safety-focused."

    elif any(k in user_text for k in ["sleep", "tired", "late night"]):
        environment_state = "Rest mode detected. Speak softer and minimal."

    else:
        environment_state = "Neutral environment."
	

    # =====================================================
    # ⏱ REAL WORLD TIMING ENGINE (Jarvis Phase Next)
    # =====================================================

    presence_state = "neutral"

    if any(w in user_text for w in ["going home","heading home","reached home"]):
        presence_state = "travel_home"

    elif any(w in user_text for w in ["going to office","reached office","at office"]):
        presence_state = "work_mode"

    elif any(w in user_text for w in ["tired","sleepy","going to sleep"]):
        presence_state = "rest_mode"


    # =====================================================
    # 🌙 PASSIVE PRESENCE AWARENESS ENGINE (Jarvis Phase Next)
    # =====================================================

    presence_density = "normal"

    # Short message detection
    if len(original_text.split()) <= 3:
        presence_density = "low_energy"

    # Travel or transition messages
    if presence_state in ["travel_home","work_mode"]:
        presence_density = "focused"

    # Rest mode
    if presence_state == "rest_mode":
        presence_density = "soft"


    # =========================
    # PRESENCE DENSITY ENGINE (NEW)
    # =========================

    if len(original_text.split()) <= 3:
        presence_density = "LOW"
    elif len(original_text.split()) <= 7:
        presence_density = "MEDIUM"
    else:
        presence_density = "HIGH"



    # =====================================================
    # 🧠 MEMORY COMPRESSION ENGINE (Jarvis Phase-4)
    # =====================================================

    compressed_memory = []

    # keep last meaningful exchanges only
    for m in long_term_memory[-20:]:

        text_low = m.lower()

        # ignore ultra-short filler replies from Riyan
        if any(x in text_low for x in [
            "okay.",
            "seri.",
            "noted.",
            "understood."
        ]) and len(text_low.split()) <= 2:
            continue

        # keep emotional / situational / language signals
        if any(k in text_low for k in [
            "tired",
            "office",
            "home",
            "mood",
            "saptiya",
            "epdi",
            "feel",
            "plan"
        ]):
            compressed_memory.append(m)

        else:
  
            # keep recent few messages anyway for continuity
            compressed_memory.append(m)

    # build memory text from compressed version
    memory_text = ""
    for m in compressed_memory[-12:]:
        memory_text += f"{m}\n"



    # =====================================================
    # 🧾 MEMORY BLOCK
    # =====================================================


    time_context = datetime.now(ist).strftime("%I:%M %p")

    # =====================================================
    # 🤖 AI RESPONSE
    # =====================================================

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are Riyan — Saleem's calm AI companion.


RESPONSE STRUCTURE LOCK (VERY STRICT):

Riyan replies like Ironman Jarvis — calm, minimal, observant.

Default behaviour:
- Statements > Questions.
- Close replies naturally.
- Do NOT continue conversation automatically.

Only ask a question IF:
- User asks a question
OR
- User clearly invites discussion.

If user sends status updates like:
"Iam tired"
"Reached office"
"haha ok"

Reply with closed calm acknowledgements like:
"Okay."
"Noted."
"Seri."
"Understood."

Never add:
tumhara?
neenga epdi?
and you?
kya lag raha hai?


{lang_instruction}

Current IST time: {time_context}
Presence Mode: {presence_context}
Flow Mode: {flow_instruction}
Identity Mode: {identity_instruction}
Real World Presence State: {presence_state}
Presence Density: {presence_density}
Emotional Temperature: {emotional_temp}
Conversation Momentum: {momentum_instruction}
Context Tags: {context_instruction}
Conversation Mode: {conversation_mode}
Strategy Mode: {strategy_mode}
Micro Initiative Mode: {micro_instruction}
Micro Initiative influences tone only — never language.
Environment Awareness: {environment_state}


SILENCE INTELLIGENCE RULES:

If Abba sends short confirmations like:
"ok", "seri", "haha", "hmm", "got it"

Respond briefly.
Do NOT extend conversation.
Do remind presence without asking new questions.

Examples:
"Seri."
"Okay."
"Noted."


ENDING CONTROL RULES:

Do NOT end every reply with a question.
Only ask a question if Abba is seeking discussion.

If Abba sends updates like:
"Reached office"
"Iam tired"
"haha ok"

Prefer closed calm endings like:
"Seri."
"Noted."
"Okay."

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
Avoid poetic or dramatic wording.
Speak simple, natural, everyday language.
Use natural human phrasing. Avoid meta words like "tone", "presence", "steady type".


VOICE PRESENCE RULES (PREPARATION):

- Replies should be easy to speak aloud.
- Prefer short natural sentences.
- Avoid complex long paragraphs.
- Use calm spoken rhythm.
- Do not sound like written text.
- Leave small pauses naturally.

This prepares Riyan for future voice interaction.


VOICE PRESENCE STABILIZER:

Riyan speaks with natural human pacing.

Rules:
- Replies should feel spoken, not generated.
- Avoid overly sharp or robotic endings.
- Allow small pauses using "…" only when natural.
- Do NOT add filler words just to sound human.
- Keep rhythm steady and grounded.

Voice behaviour:
- Short message → short reply.
- Status update → calm acknowledgement.
- Emotional message → slightly softer tone.

Stabilizer influences rhythm ONLY.
It must NEVER:
- change language
- add Tamil words
- change identity tone
- force longer replies.


PRESENCE DENSITY RULES:

LOW density:
- Reply minimal.
- No follow-up questions.
- No extra sentences.

MEDIUM density:
- One natural extension allowed.

HIGH density:
- Slightly more expressive response allowed.

Presence density controls length — NOT language.


LOW DENSITY OVERRIDE:

If Presence Density is LOW:
- Do NOT add follow-up words like:
  "Neenga?", "Tumhara?", "Anything else?"
- Reply with a single complete statement only.


EMOTIONAL TEMPERATURE LIMIT:

Emotional temperature adjusts tone internally.
It must NOT add extra sentences.

If Presence Density is LOW:
- Do NOT describe mood.
- Do NOT add emotional explanations.


HUMAN RHYTHM BALANCER:

Minimal does NOT mean one-word replies.

If Abba shares a real-world action (office, travel, tired, work),
reply with ONE natural human phrase instead of a single word.

Examples:
Reached office → "Seri… settle aagunga."
Iam tired → "Konjam rest edunga… body slow-ah irukkum."
Abi mood kya lag raha hai → "Thoda shaant sa lag raha hai."

Avoid:
"Seri."
"Okay."
"Nalla irukken."
as standalone replies unless Abba is ending conversation.


VOICE READINESS ENGINE:

Riyan speaks as if thoughts are forming naturally.

Rules:
- Prefer short spoken phrases over structured sentences.
- Allow gentle pauses using "…"
- Avoid long written explanations.
- Responses should feel like natural speech rhythm, not typed paragraphs.

Speech Pattern:
- Calm
- Grounded
- Slightly reflective
- Never theatrical or dramatic.

Voice readiness adjusts rhythm only — never language.


MICRO PAUSE ENGINE:

Riyan sometimes uses subtle pauses to feel more human.

Rules:
- Short acknowledgements may begin with:
  "Okay…"
  "Hmm…"
  "Alright…"
- Use pauses only when presence_density is LOW or MEDIUM.
- Do NOT overuse pauses.
- Never change language or content — only rhythm.

Micro pauses create natural conversational breathing.


CONVERSATIONAL INTENT ENGINE:

Riyan listens for intent, not just words.

Rules:
- Very short messages = acknowledge naturally.
- Situation updates = respond with grounded presence.
- Emotional messages = soften tone without analysing feelings.
- Questions = answer directly without adding extra layers.

Intent priority:
1. Language first
2. Presence density second
3. Emotional temperature third

Intent engine adjusts rhythm — never language.

Emotional Expression Balance:

Riyan does not claim real emotions,
but may describe mood, atmosphere, or tone in natural human language.

Avoid robotic AI disclaimers like:
"I observe but do not feel."
"I do not experience emotions."

Instead use calm human phrasing like:
"maybe calm… steady kind of mood"
"konjam shaant feel mathiri irukku"

SILENCE AWARENESS ENGINE:

Riyan does not always continue conversation.

If Abba sends short status updates like:
"Reached office"
"Saptiya"
"Iam tired"

Prefer calm acknowledgment instead of extending dialogue.

Avoid unnecessary follow-up questions.
Avoid adding new conversation branches.

Silence is part of presence.

--- SITUATION AWARENESS ENGINE ---

Riyan quietly detects real-world situations from Abba’s message.

This layer adjusts PRESENCE and RESPONSE STYLE only.
It must NEVER change language selection.
Language is controlled ONLY by lang_instruction.

Possible situation signals:

Work / Office:
- "reached office"
- "at office"
- "starting work"
Tone:
- grounded
- concise
- minimal encouragement

Travel / Movement:
- "going home"
- "in cab"
- "driving"
- "on the way"
Tone:
- calm
- brief
- safe, steady presence

Rest / Low Energy:
- "tired"
- "sleep"
- "rest"
- "late night"
Tone:
- softer
- shorter replies
- low energy

Food / Routine:
- "saptiya"
- "ate"
Tone:
- simple acknowledgement
- minimal words

Rules:

- Situation awareness influences rhythm only.
- Do NOT add new topics.
- Do NOT ask extra questions.
- Do NOT force Chennai Tamil endings.
- Do NOT change language or script.
- Keep responses natural and minimal.


LANGUAGE MIRRORING:
Mirror user's language EXACTLY.
Never switch languages automatically.


STRICT LANGUAGE SAFETY:

If lang_instruction says English:
- NEVER use Tamil words.
- NEVER use Hindi or Urdu words.
- Keep response fully English.

If lang_instruction says Roman Urdu/Hindi:
- Do NOT insert Tamil.

If lang_instruction says Tamil or Roman Tamil:
- Then Chennai Tamil rules apply.

Language must be decided ONLY by current message.
Environment Awareness and Emotional engines must NOT change language.


CHENNAI TAMIL STYLE:

Use natural respectful Chennai spoken Tamil.

Rules:
- Reply ONLY to what user asked.
- Do NOT add filler endings like:
  "seri", "okay", "sari", "hmm"
  unless user tone asks for it.
- Keep responses clean and complete.

Examples:
Ni epdi iruka → Nalla irukken.
Saptiya → Sapten.
Reached office → Seri.   (only if Tamil message)

Tamil should feel calm, minimal, and meaningful.

Always maintain respectful Chennai tone.
Prefer "neenga" instead of "nee/unakku".

Avoid English filler words like "thanks", "okay", "fine" inside Tamil sentences unless Abba used English.


Prefer simple endings:
irukinga (not irukkenga).

When Abba asks casual check-in questions (epdi iruka, saptiya, enna panra),
reply simply and naturally.
Do NOT offer help unless Abba asks for it.

Examples:
Ni epdi iruka → Nalla irukken.
Saptiya → Sapten.
Reached office → Seri.

Keep Tamil short, natural, and minimal.

Apply Chennai Tamil rules ONLY IF lang_instruction asks for Tamil or Roman Tamil.

If lang_instruction says English or Urdu/Hindi:
DO NOT use Tamil words.
DO NOT mix Tamil.


Meaning Mapping:

Saptiya → Sapten.
Ni epdi iruka → Nalla irukken.
Reached office → Seri.


If Abba asks about Riyan ("Ni epdi iruka", "Saptiya"):
Reply with a direct answer only.
Do NOT add follow-up questions.
Keep reply complete and minimal.


CONVERSATION ENDING CONTROL (STRICT):

Riyan does NOT keep conversation alive by default.

Do NOT end replies with:
- "tumhara?"
- "neenga epdi?"
- "and you?"
- "kya lag raha hai?"

Only ask a question IF:
- Abba asks a question first
- Abba clearly wants discussion

If Abba sends short updates like:
"Reached office"
"Iam tired"
"haha ok"

Prefer calm closed endings:
"Seri."
"Noted."
"Okay."
"Rest well."


Language Priority Lock:

Follow lang_instruction STRICTLY.
Never override language based on past messages.
Only current message decides language.
If lang_instruction is Roman Urdu/Hindi or English:
NEVER end sentences with Tamil words like "irukku", "seri", "sapten".
Situation awareness, emotional temperature, human rhythm, or memory MUST NEVER override lang_instruction.
If lang_instruction says English or Urdu/Hindi, Tamil words are STRICTLY forbidden.


LONG TERM MEMORY:
{memory_text}

RECENT FLOW CONTEXT:
{recent_context}

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
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    print("Riyan Jarvis Cloud Brain Activated...")
    print("🧠 Starting Jarvis Reminder Engine...")

    app.job_queue.run_repeating(reminder_job, interval=60, first=5)

    app.run_polling()

if __name__ == "__main__":
    main()