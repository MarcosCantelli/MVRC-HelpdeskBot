from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

load_dotenv()
    
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bem-vindo ao Help Desk!\nDigite seu problema:"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.username
    text = update.message.text

    response = requests.post(
        "http://localhost:5000/ticket",
        json={"user": user, "description": text}
    )

    data = response.json()

    await update.message.reply_text(
        f"Chamado #{data['id']} criado com sucesso!"
    )

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()