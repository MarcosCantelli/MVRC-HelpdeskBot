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
}


# =========================
# UTILS
# =========================
def mensagem_padrao():
    return "Não entendi sua solicitação. Entre em contato com o suporte."


def problema_simples(texto: str) -> bool:
    if not texto:
        return False

    texto = texto.lower()

    palavras_simples = ["lento", "internet", "wifi", "reiniciar"]
    return any(p in texto for p in palavras_simples)


# =========================
# IA SIMPLES
# =========================
def sugerir_solucao(texto):
    if not texto:
        return "💡 Sugestão: verificar o equipamento e reiniciar."

    texto = texto.lower()

    if "lento" in texto:
        return "💻 Sugestão: reiniciar o computador."

    if "internet" in texto:
        return "🌐 Sugestão: reiniciar o roteador."

    return "💡 Sugestão: verificar e reiniciar o dispositivo."


# =========================
# PAYLOAD
# =========================
def criar_payload(user, context):
    context = context or {}

    return {
        "user": user,
        "description": context.get("descricao"),
        "category": context.get("categoria"),
        "subcategory": context.get("dispositivo"),
        "ai_suggestion": context.get("sugestao")
    }


# =========================
# API
# =========================
def enviar_ticket(payload, request_func=None):
    request_func = request_func or requests.post

    try:
        response = request_func(API_URL, json=payload)
        return response.json() if hasattr(response, "json") else None
    except Exception:
        return None


def notificar_telegram(user, ticket_id, request_func=None):
    if not TELEGRAM_CHAT_ID:
        return None

    request_func = request_func or requests.post

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
# TICKET
# =========================
async def criar_ticket(update, user, context):
    payload = criar_payload(user, context)
    data = enviar_ticket(payload)

    if data and data.get("id"):
        await update.message.reply_text(f"🎟️ Chamado #{data['id']} criado!")
        notificar_telegram(user, data["id"])
    else:
        await update.message.reply_text("❌ Erro ao criar chamado.")


# =========================
# BOT (FLUXO COM ESTADO)
# =========================
def run_bot(token=None):
    token = token or TOKEN

    if not token:
        raise ValueError("TOKEN do Telegram não configurado")

    app = ApplicationBuilder().token(token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        context.user_data["step"] = "tipo"

        keyboard = [["🖥️ Hardware", "💻 Software"]]

        await update.message.reply_text(
            "Bem-vindo ao HelpDesk! O problema é hardware ou software?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        step = context.user_data.get("step")

        # =========================
        # ESCOLHA TIPO
        # =========================
        if step == "tipo":
            if "hardware" in text.lower():
                context.user_data["categoria"] = "hardware"
                context.user_data["step"] = "equipamento"

                keyboard = [["Computador", "Notebook"], ["Celular", "Impressora", "Modem"]]

                await update.message.reply_text(
                    "Certo, qual equipamento?",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            if "software" in text.lower():
                context.user_data["categoria"] = "software"
                context.user_data["step"] = "descricao"

                await update.message.reply_text(
                    "Certo, descreva o problema em detalhes."
                )
                return

        # =========================
        # HARDWARE → EQUIPAMENTO
        # =========================
        if step == "equipamento":
            context.user_data["dispositivo"] = text
            context.user_data["step"] = "descricao"

            await update.message.reply_text(
                f"Certo, descreva o problema com {text}."
            )
            return

        # =========================
        # DESCRIÇÃO FINAL
        # =========================
        if step == "descricao":
            context.user_data["descricao"] = text

            sugestao = sugerir_solucao(text)
            context.user_data["sugestao"] = sugestao

            await update.message.reply_text(sugestao)

            # Se simples → NÃO abre ticket ainda
            if problema_simples(text):
                await update.message.reply_text(
                    "Isso pode ser resolvido com a sugestão acima. Caso não funcione, me avise 👍"
                )
                context.user_data["step"] = "aguardando_confirmacao"
                return

            # Se não simples → abre ticket direto
            await criar_ticket(update, "anonimo", context.user_data)
            context.user_data["step"] = "finalizado"
            return

        # =========================
        # CONFIRMAÇÃO
        # =========================
        if step == "aguardando_confirmacao":
            if "não" in text.lower():
                await criar_ticket(update, "anonimo", context.user_data)
                context.user_data["step"] = "finalizado"
            else:
                await update.message.reply_text("Perfeito! 👍")
                context.user_data["step"] = "finalizado"

            return

        # fallback
        await update.message.reply_text(mensagem_padrao())

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    return app


if __name__ == "__main__":
    app = run_bot()
    app.run_polling()


__all__ = [
    "mensagem_padrao",
    "sugerir_solucao",
    "criar_payload",
    "enviar_ticket",
    "criar_ticket",
    "notificar_telegram",
    "problema_simples",
    "run_bot"
]