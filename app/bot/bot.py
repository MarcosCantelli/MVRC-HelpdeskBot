from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import requests
import os
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://helpdesk-api:5000")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 🔥 ADMIN VIA ID (JENKINS)
ADMIN_IDS = [x.strip() for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]


# =========================
# FAQ
# =========================
FAQ = {
    "internet lenta": "🔌 Reiniciar o roteador e verificar os cabos.",
    "computador não liga": "⚡ Verificar fonte e cabo de energia.",
    "impressora não imprime": "🖨️ Impressora: verificar conexão e tinta.",
}


def mensagem_padrao():
    return "Não entendi sua solicitação. Entre em contato com o suporte."


# =========================
# USER SAFE + ID
# =========================
def get_user(update):
    if hasattr(update, "effective_user") and update.effective_user:
        return (
            getattr(update.effective_user, "full_name", None)
            or getattr(update.effective_user, "username", None)
            or "anonimo"
        )
    return "anonimo"


def get_user_id(update):
    if hasattr(update, "effective_user") and update.effective_user:
        return str(update.effective_user.id)
    return "0"


def is_admin(update):
    return get_user_id(update) in ADMIN_IDS


# =========================
# IA SIMPLES
# =========================
def sugerir_solucao(texto):
    if not texto:
        return "💡 Sugestão: verificar o equipamento e reiniciar."

    texto = texto.lower()

    if "internet" in texto or "wifi" in texto:
        return "🌐 Sugestão: reiniciar o roteador ou modem."

    if "lento" in texto or "travando" in texto:
        return "💻 Sugestão: reiniciar o computador."

    return "💡 Sugestão: verificar o problema e reiniciar o dispositivo."


# =========================
# RESPOSTA AUTOMÁTICA
# =========================
def responder_automatico(texto):
    if not texto:
        return mensagem_padrao()

    texto = texto.lower()

    if "sem conexão" in texto or "sem internet":
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
        "não imprime",
        "travando",
        "wifi fraco",
        "internet lenta"
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
    request_func = request_func or requests.post

    try:
        response = request_func(f"{API_URL}/ticket", json=payload, timeout=5)
        return response.json() if response else None
    except:
        return None


def listar_tickets():
    try:
        return requests.get(f"{API_URL}/tickets").json()
    except:
        return []


def fechar_ticket(ticket_id, admin, note=""):
    try:
        return requests.post(
            f"{API_URL}/ticket/{ticket_id}/close",
            json={"admin": admin, "notes": note}
        ).json()
    except:
        return None


# =========================
# TELEGRAM NOTIFICAÇÃO
# =========================
def notificar_telegram(user, ticket_code, request_func=None):
    if not TELEGRAM_CHAT_ID:
        return None

    request_func = request_func or requests.post

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"🚨 Novo chamado!\n👤 {user}\n🎟️ {ticket_code}"
        }

        return request_func(url, json=payload)
    except:
        return None


# =========================
# CRIAÇÃO DE TICKET
# =========================
async def criar_ticket(update, user, context):
    try:
        payload = criar_payload(user, context)
        data = enviar_ticket(payload)

        if data and data.get("id"):
            codigo = data.get("ticket_code")

            await update.message.reply_text(f"🎟️ Chamado {codigo} criado!")
            notificar_telegram(user, codigo)
        else:
            await update.message.reply_text("❌ Erro ao criar chamado.")

    except:
        await update.message.reply_text("❌ Erro ao criar chamado.")


# =========================
# BOT
# =========================
def run_bot(token=None):
    token = token or TOKEN
    app = ApplicationBuilder().token(token).build()

    # =========================
    # START
    # =========================
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        context.user_data["step"] = "tipo"

        keyboard = [["🖥️ Hardware", "💻 Software"]]

        await update.message.reply_text(
            "Bem-vindo! O problema é hardware ou software?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    # =========================
    # ADMIN - LISTAR
    # =========================
    async def tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("❌ Acesso negado.")
            return

        data = listar_tickets()

        if not data:
            await update.message.reply_text("Nenhum ticket encontrado.")
            return

        msg = "\n".join([
            f"{t['id']} | {t['code']} | {t['status']} | {t['user']}"
            for t in data
        ])

        await update.message.reply_text(msg)

    # =========================
    # ADMIN - FECHAR
    # =========================
    async def close(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("❌ Acesso negado.")
            return

        if not context.args:
            await update.message.reply_text("Use: /close <id> observação")
            return

        ticket_id = context.args[0]
        note = " ".join(context.args[1:]) if len(context.args) > 1 else ""

        admin = get_user(update)

        fechar_ticket(ticket_id, admin, note)

        await update.message.reply_text(f"✅ Ticket {ticket_id} fechado.")

    # =========================
    # HANDLER PRINCIPAL
    # =========================
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text or ""
        step = context.user_data.get("step", "tipo")

        user = get_user(update)

        if step == "tipo":
            lower = text.lower()

            if "hardware" in lower:
                context.user_data["categoria"] = "hardware"
                context.user_data["step"] = "equipamento"

                keyboard = [["Computador", "Notebook", "Impressora"]]

                await update.message.reply_text(
                    "Qual equipamento?",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            if "software" in lower:
                context.user_data["categoria"] = "software"
                context.user_data["step"] = "descricao"

                await update.message.reply_text("Descreva o problema:")
                return

            await update.message.reply_text("Escolha Hardware ou Software.")
            return

        if step == "equipamento":
            context.user_data["dispositivo"] = text
            context.user_data["step"] = "descricao"

            await update.message.reply_text(f"Descreva o problema no {text}:")
            return

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
                await criar_ticket(update, user, context.user_data)
                context.user_data["step"] = "finalizado"

            return

        if step == "aguardando_confirmacao":
            if "sim" in text.lower():
                context.user_data["step"] = "finalizado"
                await update.message.reply_text("✅ Perfeito!")
            else:
                await criar_ticket(update, user, context.user_data)
                context.user_data["step"] = "finalizado"

            return

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tickets", tickets))
    app.add_handler(CommandHandler("close", close))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    return app


if __name__ == "__main__":
    app = run_bot()
    app.run_polling()