from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

FAQ = {
    "internet lenta": "🔌 Reinicie o roteador e verifique os cabos.",
    "computador não liga": "⚡ Verifique fonte e cabo de energia.",
    "impressora não imprime": "🖨️ Verifique conexão e tinta.",
    "filamento": "🧵 Verifique se o filamento não travou.",
}


def responder_automatico(texto: str):
    if not texto:
        return None

    texto = texto.lower()
    for chave in FAQ:
        if chave in texto:
            return FAQ[chave]
    return None


def criar_payload(user, context):
    return {
        "user": user,
        "description": context.get("descricao"),
        "category": context.get("category"),
        "subcategory": context.get("subcategory"),
        "ai_suggestion": context.get("ai")
    }


async def criar_ticket(update, user, context):
    try:
        payload = criar_payload(user, context)

        response = requests.post(
            "http://helpdesk-api:5000/ticket",
            json=payload
        )

        data = response.json()

        await update.message.reply_text(
            f"🎟️ Chamado #{data.get('id')} criado!"
        )

    except Exception:
        await update.message.reply_text("❌ Erro ao criar chamado.")


# 🔥 Só executa o bot se rodar diretamente (NÃO nos testes)
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [["🖥️ Hardware", "💻 Software"]]

        await update.message.reply_text(
            "Bem-vindo ao HelpDesk",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text

        resposta = responder_automatico(text)

        if resposta:
            await update.message.reply_text(resposta)
        else:
            await criar_ticket(update, "anonimo", context.user_data)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    app.run_polling()