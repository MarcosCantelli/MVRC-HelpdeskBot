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


def responder_automatico(texto):
    if not texto:
        return "Não entendi sua solicitação. Entre em contato com o suporte."

    texto = texto.lower()

    # 🔥 usa FAQ primeiro (aumenta coverage)
    for pergunta, resposta in FAQ.items():
        if pergunta in texto:
            return resposta

    if "internet" in texto:
        return "🔌 Reiniciar o roteador pode ajudar. Verifique também os cabos."

    if "sem conexão" in texto or "sem internet" in texto:
        return "❌ Verifique sua conexão ou reinicie o roteador."

    return "Não entendi sua solicitação. Entre em contato com o suporte."


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