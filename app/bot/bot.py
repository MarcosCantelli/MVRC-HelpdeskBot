from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://helpdesk-api:5000/ticket")

FAQ = {
    "internet lenta": "🔌 Reiniciar o roteador e verificar os cabos.",
    "computador não liga": "⚡ Verificar fonte e cabo de energia.",
    "impressora não imprime": "🖨️ Impressora: verificar conexão e tinta.",
    "filamento": "🧵 Verificar se o filamento não travou.",
}


def mensagem_padrao():
    return "Não entendi sua solicitação. Entre em contato com o suporte."


def responder_automatico(texto):
    if not texto:
        return mensagem_padrao()

    texto = texto.lower()

    for chave, resposta in FAQ.items():
        if chave in texto:
            return resposta

    if "sem conexão" in texto or "sem internet" in texto:
        return "❌ Verificar conexão ou reiniciar o roteador."

    if "internet" in texto:
        return "🔌 Reiniciar o roteador pode ajudar. Verificar também os cabos."

    return mensagem_padrao()


def criar_payload(user, context):
    context = context or {}

    return {
        "user": user,
        "description": context.get("descricao"),
        "category": context.get("category"),
        "subcategory": context.get("subcategory"),
        "ai_suggestion": context.get("ai")
    }


def enviar_ticket(payload, request_func=None):
    if request_func is None:
        request_func = requests.post

    try:
        response = request_func(API_URL, json=payload)

        # 🔥 compatível com mock e requests real
        if hasattr(response, "json"):
            return response.json()

        return None

    except Exception:
        return None


async def criar_ticket(update, user, context):
    try:
        payload = criar_payload(user, context)
        data = enviar_ticket(payload)

        if data and data.get("id"):
            await update.message.reply_text(
                f"🎟️ Chamado #{data.get('id')} criado!"
            )
        else:
            await update.message.reply_text("❌ Erro ao criar chamado.")

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