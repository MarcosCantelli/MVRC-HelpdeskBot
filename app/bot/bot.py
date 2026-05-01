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


def mensagem_padrao():
    return "Não entendi sua solicitação. Entre em contato com o suporte."


# =========================
# IA SIMPLES
# =========================
def sugerir_solucao(texto):
    if not texto:
        return "💡 Sugestão: verificar o equipamento e reiniciar."

    texto = texto.lower()

    if "lento" in texto or "lenta" in texto:
        return "💻 Sugestão: reiniciar o computador."

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

    if "sem conexão" in texto or "sem internet" in texto:
        return "❌ Verificar conexão ou reiniciar o roteador."

    for chave, resposta in FAQ.items():
        if chave in texto:
            return resposta

    if "internet" in texto:
        return "🔌 Reiniciar o roteador pode ajudar."

    return mensagem_padrao()


# =========================
# DETECTAR COMPLEXIDADE
# =========================
def problema_simples(texto):
    if not texto:
        return False

    texto = texto.lower()

    simples = [
        "lento",
        "lenta",
        "internet lenta",
        "não imprime",
        "travando",
        "wifi fraco"
    ]

    return any(s in texto for s in simples)


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
                "text": f"🚨 Novo chamado!\n👤 {user}\n🎟️ #{ticket_id}"
            }
        )
    except Exception:
        return None


# =========================
# CRIAÇÃO DE TICKET
# =========================
async def criar_ticket(update, user, context):
    payload = criar_payload(user, context)

    try:
        data = enviar_ticket(payload)
    except Exception:
        data = None

    if data and data.get("id"):
        await update.message.reply_text(f"🎟️ Chamado #{data['id']} criado!")
        notificar_telegram(user, data["id"])
    else:
        await update.message.reply_text("❌ Erro ao criar chamado.")


# =========================
# BOT
# =========================
def run_bot(token=None):
    token = token or TOKEN

    app = ApplicationBuilder().token(token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        context.user_data["step"] = "tipo"

        keyboard = [["🖥️ Hardware", "💻 Software"]]

        await update.message.reply_text(
            "Bem-vindo! O problema é hardware ou software?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        step = context.user_data.get("step")

        # 🔥 Corrige step None (testes começam sem estado)
        if not step:
            context.user_data["step"] = "tipo"
            await update.message.reply_text("Escolha Hardware ou Software.")
            return

        # =========================
        # STEP 1 - tipo
        # =========================
        if step == "tipo":
            if "hardware" in text.lower():
                context.user_data["categoria"] = "hardware"
                context.user_data["step"] = "equipamento"

                keyboard = [["Computador", "Notebook", "Impressora"]]

                await update.message.reply_text(
                    "Qual equipamento?",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            if "software" in text.lower():
                context.user_data["categoria"] = "software"
                context.user_data["step"] = "descricao"

                await update.message.reply_text("Descreva o problema:")
                return

            # 🔥 fallback obrigatório
            await update.message.reply_text("Escolha Hardware ou Software.")
            return

        # =========================
        # STEP 2 - equipamento
        # =========================
        if step == "equipamento":
            context.user_data["dispositivo"] = text
            context.user_data["step"] = "descricao"

            await update.message.reply_text(f"Descreva o problema no {text}:")
            return

        # =========================
        # STEP 3 - descricao
        # =========================
        if step == "descricao":
            context.user_data["descricao"] = text

            resposta = responder_automatico(text)
            sugestao = sugerir_solucao(text)

            await update.message.reply_text(resposta)
            await update.message.reply_text(sugestao)

            if problema_simples(text):
                context.user_data["step"] = "aguardando_confirmacao"
                await update.message.reply_text("Isso resolveu? (sim/não)")
            else:
                await criar_ticket(update, "anonimo", context.user_data)
                context.user_data["step"] = "finalizado"

            return

        # =========================
        # STEP 4 - confirmação
        # =========================
        if step == "aguardando_confirmacao":
            if "sim" in text.lower():
                context.user_data["step"] = "finalizado"
                await update.message.reply_text("✅ Perfeito!")
            elif "não" in text.lower() or "nao" in text.lower():
                await criar_ticket(update, "anonimo", context.user_data)
                context.user_data["step"] = "finalizado"
            else:
                await update.message.reply_text("Responda com sim ou não.")
            return

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    return app


if __name__ == "__main__":
    app = run_bot()
    app.run_polling()


__all__ = [
    "responder_automatico",
    "criar_payload",
    "enviar_ticket",
    "criar_ticket",
    "sugerir_solucao",
    "notificar_telegram",
    "run_bot"
]