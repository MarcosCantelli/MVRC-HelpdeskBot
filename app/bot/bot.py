from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://helpdesk-api:5000")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

FAQ = {
    "internet lenta": "🔌 Reiniciar o roteador e verificar os cabos.",
    "computador não liga": "⚡ Verificar fonte e cabo de energia.",
    "impressora não imprime": "🖨️ Impressora: verificar conexão e tinta.",
}


# =========================
# UTIL
# =========================
def mensagem_padrao():
    return "Não entendi sua solicitação. Entre em contato com o suporte."


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
        return str(getattr(update.effective_user, "id", ""))
    return ""


def is_admin(update):
    return get_user_id(update) in ADMIN_IDS


# =========================
# IA
# =========================
def sugerir_solucao(texto):
    if not texto:
        return "💡 Sugestão: verificar o equipamento e reiniciar."

    texto = texto.lower()

    if "internet" in texto:
        return "🌐 Sugestão: reiniciar o roteador."

    if "lento" in texto or "travando" in texto:
        return "💻 Sugestão: reiniciar o computador."

    return "💡 Sugestão: verificar o problema e reiniciar o dispositivo."


def responder_automatico(texto):
    if not texto:
        return mensagem_padrao()

    texto = texto.lower()

    # 🔥 REGRA MAIS ESPECÍFICA PRIMEIRO (CORREÇÃO DO CI)
    if "sem conexão" in texto or "sem internet" in texto:
        return "❌ Verificar conexão ou reiniciar o roteador."

    for chave, resposta in FAQ.items():
        if chave in texto:
            return resposta

    if "internet" in texto:
        return "🔌 Reiniciar o roteador pode ajudar."

    return mensagem_padrao()


def problema_simples(texto):
    if not texto:
        return False

    texto = texto.lower()

    simples = ["lento", "travando", "internet lenta"]

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
        "ai_suggestion": context.get("sugestao") or context.get("ai"),
    }


# =========================
# API
# =========================
def enviar_ticket(payload, request_func=None):
    request_func = request_func or requests.post

    try:
        try:
            response = request_func(f"{API_URL}/ticket", json=payload, timeout=5)
        except TypeError:
            response = request_func(f"{API_URL}/ticket", json=payload)

        if response and hasattr(response, "json"):
            return response.json()

        return None

    except Exception:
        return None


def listar_tickets():
    try:
        return requests.get(f"{API_URL}/tickets").json()
    except:
        return []


def fechar_ticket(ticket_id, admin):
    try:
        return requests.post(
            f"{API_URL}/ticket/{ticket_id}/close",
            json={"admin": admin},
        ).json()
    except:
        return None


# =========================
# NOTIFICAÇÃO
# =========================
def notificar_telegram(user, ticket_code, request_func=None):
    if not TELEGRAM_CHAT_ID:
        return None

    request_func = request_func or requests.post

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"🚨 Novo chamado!\n👤 {user}\n🎟️ {ticket_code}",
        }

        try:
            return request_func(url, json=payload, timeout=5)
        except TypeError:
            return request_func(url, json=payload)

    except Exception:
        return None


# =========================
# CRIAR TICKET
# =========================
async def criar_ticket(update, user, context):
    try:
        payload = criar_payload(user, context)

        try:
            data = enviar_ticket(payload)
        except Exception:
            data = None

        if data and data.get("id"):
            codigo = data.get("ticket_code") or f"TK{str(data['id']).zfill(3)}"

            await update.message.reply_text(f"🎟️ Chamado {codigo} criado!")
            notificar_telegram(user, codigo)
        else:
            await update.message.reply_text("❌ Erro ao criar chamado.")

    except Exception:
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
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )

    async def tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("❌ Acesso negado.")
            return

        data = listar_tickets()

        if not data:
            await update.message.reply_text("Nenhum ticket encontrado.")
            return

        msg = "\n".join(
            [f"{t['id']} | {t['code']} | {t['status']}" for t in data]
        )

        await update.message.reply_text(msg)

    async def close(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("❌ Acesso negado.")
            return

        if not context.args:
            await update.message.reply_text("Use: /close <id>")
            return

        ticket_id = context.args[0]
        fechar_ticket(ticket_id, get_user(update))

        await update.message.reply_text(f"Ticket {ticket_id} fechado.")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text or ""
        step = context.user_data.get("step", "tipo")

        user = get_user(update)

        if step == "tipo":
            if "hardware" in text.lower():
                context.user_data["categoria"] = "hardware"
                context.user_data["step"] = "equipamento"
                await update.message.reply_text("Qual equipamento?")
                return

            if "software" in text.lower():
                context.user_data["categoria"] = "software"
                context.user_data["step"] = "descricao"
                await update.message.reply_text("Descreva o problema:")
                return

            await update.message.reply_text("Escolha Hardware ou Software.")
            return

        if step == "equipamento":
            context.user_data["dispositivo"] = text
            context.user_data["step"] = "descricao"
            await update.message.reply_text("Descreva o problema:")
            return

        if step == "descricao":
            context.user_data["descricao"] = text

            await update.message.reply_text(responder_automatico(text))
            await update.message.reply_text(sugerir_solucao(text))

            if problema_simples(text):
                context.user_data["step"] = "aguardando_confirmacao"
                await update.message.reply_text("Isso resolveu? (sim/não)")
            else:
                await criar_ticket(update, user, context.user_data)
                context.user_data["step"] = "finalizado"
            return

        if step == "aguardando_confirmacao":
            if "sim" in text.lower():
                await update.message.reply_text("✅ Perfeito!")
            else:
                await criar_ticket(update, user, context.user_data)

            context.user_data["step"] = "finalizado"

    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tickets", tickets))
    app.add_handler(CommandHandler("close", close))

    return app


if __name__ == "__main__":
    app = run_bot()
    app.run_polling()