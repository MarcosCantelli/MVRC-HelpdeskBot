from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:5000")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


FAQ = {
    "internet lenta": "🔌 Reiniciar o roteador e verificar os cabos.",
    "computador não liga": "⚡ Verificar fonte e cabo de energia.",
    "impressora não imprime": "🖨️ Impressora: verificar conexão e tinta.",
    "filamento": "🧵 Verificar se o filamento não travou.",
}


def mensagem_padrao():
    return "Não entendi sua solicitação. Entre em contato com o suporte."


# =========================
# IA SIMPLES (SUGESTÕES)
# =========================
def sugerir_solucao(texto):
    if not texto:
        return "💡 Sugestão: verificar o equipamento e reiniciar."

    texto = texto.lower()

    if "lento" in texto:
        return "💻 Sugestão: reiniciar o computador e verificar energia."

    if "internet" in texto:
        return "🌐 Sugestão: reiniciar o roteador."

    return "💡 Sugestão: verificar o problema e reiniciar o dispositivo."


# =========================
# RESPOSTA AUTOMÁTICA
# =========================
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


# =========================
# PAYLOAD
# =========================
def criar_payload(user, context):
    context = context or {}

    return {
        "user": user,
        "description": context.get("descricao") or context.get("description"),
        "category": context.get("categoria") or context.get("category"),
        "subcategory": context.get("dispositivo") or context.get("subcategory"),
        "ai_suggestion": context.get("sugestao") or context.get("ai")
    }


# =========================
# API
# =========================
def enviar_ticket(payload, request_func=None):
    if request_func is None:
        request_func = requests.post

    try:
        response = request_func(API_URL, json=payload)

        if hasattr(response, "json"):
            return response.json()

        return None

    except Exception:
        return None


# =========================
# NOTIFICAÇÃO TELEGRAM (NOVO - TESTÁVEL)
# =========================
def notificar_telegram(user, ticket_id, request_func=None):
    if not TELEGRAM_CHAT_ID:
        return None

    if request_func is None:
        request_func = requests.post

    try:
        return request_func(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"🚨 Novo chamado aberto!\n👤 {user}\n🎟️ #{ticket_id}"
            }
        )
    except Exception:
        return None


# =========================
# CRIAÇÃO DE TICKET
# =========================
async def criar_ticket(update, user, context):
    try:
        payload = criar_payload(user, context)
        data = enviar_ticket(payload)

        if data and data.get("id"):
            msg = f"🎟️ Chamado #{data.get('id')} criado!"
            await update.message.reply_text(msg)

            # agora testável
            notificar_telegram(user, data.get("id"))

        else:
            await update.message.reply_text("❌ Erro ao criar chamado.")

    except Exception:
        await update.message.reply_text("❌ Erro ao criar chamado.")


# =========================
# BOT (REFATORADO)
# =========================
def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [["🖥️ Hardware", "💻 Software"]]

        await update.message.reply_text(
            "Bem-vindo ao HelpDesk! O problema é hardware ou software?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text

        context.user_data["descricao"] = text

        sugestao = sugerir_solucao(text)
        context.user_data["sugestao"] = sugestao

        resposta = responder_automatico(text)

        await update.message.reply_text(resposta)
        await update.message.reply_text(sugestao)

        await criar_ticket(update, "anonimo", context.user_data)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    return app


if __name__ == "__main__":
    run_bot().run_polling()


__all__ = [
    "responder_automatico",
    "criar_payload",
    "enviar_ticket",
    "criar_ticket",
    "sugerir_solucao",
    "notificar_telegram",
    "run_bot"
]