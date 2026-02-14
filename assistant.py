from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from openai import OpenAI

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"Your name is Riyan. You are Saleem's intelligent personal AI assistant. Speak in a smart hybrid style — professional and friendly. User said: {user_text}"
        )

        reply = response.output[0].content[0].text

    except Exception as e:
        print("OPENAI ERROR:", e)
        reply = "⚠️ Riyan cannot reach AI right now."

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(BOT_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Riyan is running...")
app.run_polling()