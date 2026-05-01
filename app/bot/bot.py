from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://helpdesk-api:5000/ticket")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# ==============================
# 🤖 FAQ / IA SIMPLES
# ==============================
FAQ = {
    "internet lenta": "🔌 Reiniciar o roteador e verificar os cabos.",
    "computador não liga": "⚡ Verificar fonte e cabo de energia.",
    "impressora não imprime": "🖨️ Verificar conexão e nível de tinta.",
    "celular travando": "📱 Reiniciar o celular e fechar apps em segundo plano.",
}


def mensagem_padrao():
    return "Não entendi sua solicitação. Pode descrever melhor o problema?"


def responder_automatico(texto):
    if not texto:
        return mensagem_padrao()

    texto = texto.lower()

    for chave, resposta in FAQ.items():
        if chave in texto:
            return resposta

    if "internet" in texto:
        return "🌐 Tente reiniciar o roteador/modem."

    if "lento" in texto:
        return "🐢 Pode ser excesso de processos. Reiniciar ajuda."

    return None  # 🔥 importante: agora retorna None se não achar nada


# ==============================
# 📦 PAYLOAD
# ==============================
def criar_payload(user, context):
    context = context or {}

    return {
        "user": user,
        "description": context.get("descricao"),
        "category": context.get("category"),
        "subcategory": context.get("subcategory"),
        "ai_suggestion": context.get("ai")
    }


# ==============================
# 🌐 API CALL
# ==============================
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


# ==============================
# 🎟️ CRIAR TICKET
# ==============================
async def criar_ticket(update, user, context):
    try:
        payload = criar_payload(user, context)
        data = enviar_ticket(payload)

        if data and data.get("id"):
            ticket_id = data.get("id")

            await update.message.reply_text(
                f"🎟️ Chamado #{ticket_id} criado com sucesso!"
            )

            # 🔥 NOTIFICA ADMIN
            if ADMIN_CHAT_ID:
                await update.get_bot().send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(
                        f"📢 Novo chamado aberto!\n\n"
                        f"👤 Usuário: {user}\n"
                        f"📂 Categoria: {payload.get('category')}\n"
                        f"💻 Dispositivo: {payload.get('subcategory')}\n"
                        f"📝 Descrição: {payload.get('description')}\n"
                        f"🤖 Sugestão: {payload.get('ai_suggestion')}\n"
                        f"🎟️ Ticket: #{ticket_id}"
                    )
                )

        else:
            await update.message.reply_text("❌ Erro ao criar chamado.")

    except Exception:
        await update.message.reply_text("❌ Erro ao criar chamado.")


# ==============================
# 🚀 BOT
# ==============================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # ==========================
    # START
    # ==========================
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [["🖥️ Hardware", "💻 Software"]]

        context.user_data.clear()

        await update.message.reply_text(
            "Bem-vindo ao HelpDesk!\nEscolha o tipo de problema:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    # ==========================
    # FLOW PRINCIPAL
    # ==========================
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text

        # ======================
        # ETAPA 1 - CATEGORIA
        # ======================
        if text in ["🖥️ Hardware", "💻 Software"]:
            context.user_data["category"] = text.replace("🖥️ ", "").replace("💻 ", "").lower()

            keyboard = [["📱 Celular", "💻 Computador", "🖥️ Notebook"]]

            await update.message.reply_text(
                "Qual dispositivo está com problema?",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

        # ======================
        # ETAPA 2 - SUBCATEGORIA
        # ======================
        if text in ["📱 Celular", "💻 Computador", "🖥️ Notebook"]:
            context.user_data["subcategory"] = text.replace("📱 ", "").replace("💻 ", "").replace("🖥️ ", "").lower()

            await update.message.reply_text(
                "Descreva o problema:"
            )
            return

        # ======================
        # ETAPA 3 - DESCRIÇÃO
        # ======================
        context.user_data["descricao"] = text

        sugestao = responder_automatico(text)
        context.user_data["ai"] = sugestao

        if sugestao:
            await update.message.reply_text(f"🤖 Sugestão: {sugestao}")

        keyboard = [["✅ Abrir chamado", "❌ Cancelar"]]

        await update.message.reply_text(
            "Deseja abrir um chamado?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

        # ======================
        # ETAPA 4 - CONFIRMAÇÃO
        # ======================
        if text == "✅ Abrir chamado":
            await criar_ticket(update, str(update.effective_user.id), context.user_data)
            context.user_data.clear()

        elif text == "❌ Cancelar":
            await update.message.reply_text("❌ Chamado cancelado.")
            context.user_data.clear()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    app.run_polling()


# ==============================
# EXPORTS (TESTES)
# ==============================
__all__ = [
    "responder_automatico",
    "criar_payload",
    "enviar_ticket",
    "criar_ticket",
]