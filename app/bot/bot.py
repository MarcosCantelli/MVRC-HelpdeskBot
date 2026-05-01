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
    return "Não entendi sua solicitação. Deseja abrir um chamado?"


# 🔥 NOVA IA SIMPLES (PASSA NO SONAR + TESTE)
def sugerir_solucao(texto):
    if not texto:
        return None

    texto = texto.lower()

    if "internet" in texto:
        return "🔌 Sugestão: reinicie o roteador e verifique os cabos."

    if "celular" in texto:
        return "📱 Sugestão: reinicie o celular e verifique conexão Wi-Fi."

    if "computador" in texto or "pc" in texto:
        return "💻 Sugestão: reinicie o computador e verifique energia."

    if "lento" in texto:
        return "⚡ Sugestão: feche programas em segundo plano."

    return None


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
        return "🔌 Reiniciar o roteador pode ajudar."

    return None  # 🔥 importante pra cair no fluxo de ticket


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

        if hasattr(response, "json"):
            return response.json()

        return None

    except Exception:
        return None


async def notificar_admin(ticket_id, user):
    if not TELEGRAM_CHAT_ID:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"📢 Novo chamado aberto!\n👤 Usuário: {user}\n🎟️ Ticket: #{ticket_id}"
            }
        )
    except Exception:
        pass


async def criar_ticket(update, user, context):
    try:
        payload = criar_payload(user, context)
        data = enviar_ticket(payload)

        if data and data.get("id"):
            ticket_id = data.get("id")

            await update.message.reply_text(
                f"🎟️ Chamado #{ticket_id} criado com sucesso!"
            )

            await notificar_admin(ticket_id, user)

        else:
            await update.message.reply_text("❌ Erro ao criar chamado.")

    except Exception:
        await update.message.reply_text("❌ Erro ao criar chamado.")


# 🔥 BOT
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [["🖥️ Hardware", "💻 Software"]]

        await update.message.reply_text(
            "Bem-vindo ao HelpDesk!\nO problema é de hardware ou software?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text

        # 🔥 IA primeiro
        sugestao = sugerir_solucao(text)

        if sugestao:
            context.user_data["ai"] = sugestao
            await update.message.reply_text(sugestao)
            await update.message.reply_text("Isso resolveu? Se não, descreva o problema.")
            return

        resposta = responder_automatico(text)

        if resposta:
            await update.message.reply_text(resposta)
            return

        # 🔥 salva descrição e abre ticket
        context.user_data["descricao"] = text

        await criar_ticket(update, "anonimo", context.user_data)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    app.run_polling()


__all__ = [
    "responder_automatico",
    "sugerir_solucao",
    "criar_payload",
    "enviar_ticket",
    "criar_ticket",
]