from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

# 🧠 Base simples de conhecimento (IA básica)
FAQ = {
    "internet lenta": "🔌 Verifique o cabo de rede ou reinicie o roteador.",
    "computador não liga": "⚡ Verifique o cabo de energia e a fonte.",
    "impressora não imprime": "🖨️ Verifique conexão USB ou rede e nível de tinta.",
    "erro windows": "💻 Tente reiniciar o computador e verificar atualizações.",
    "filamento": "🧵 Verifique se o filamento não está preso ou quebrado."
}


def responder_automatico(texto):
    texto = texto.lower()

    for chave in FAQ:
        if chave in texto:
            return FAQ[chave]

    return None


# 🚀 /start com menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🖥️ Hardware", "💻 Software"],
        ["🖨️ Impressão 3D"]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    mensagem = """
👋 Olá! Bem-vindo ao *Help Desk MVRC*

Estou aqui para te ajudar com problemas técnicos 🚀

Escolha uma categoria abaixo ou descreva seu problema:

🖥️ Hardware  
💻 Software  
🖨️ Impressão 3D  

💡 Vou tentar te ajudar automaticamente antes de abrir um chamado 😉
"""

    await update.message.reply_text(
        mensagem,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


# 🎯 Captura categoria
async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "Hardware" in text:
        context.user_data["categoria"] = "hardware"
        await update.message.reply_text("🔧 Descreva seu problema de hardware:")

    elif "Software" in text:
        context.user_data["categoria"] = "software"
        await update.message.reply_text("💻 Qual software está com problema?")

    elif "Impressão 3D" in text:
        context.user_data["categoria"] = "impressao_3d"
        await update.message.reply_text("🖨️ O que você deseja imprimir ?")


# 🤖 Fluxo principal
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.username or "anonimo"
    text = update.message.text

    # 🔹 Se for escolha de menu
    if any(cat in text for cat in ["Hardware", "Software", "Impressão"]):
        await handle_category(update, context)
        return

    # 🔹 Se usuário respondeu "sim" ou "não"
    if context.user_data.get("aguardando_confirmacao"):
        if text.lower() == "sim":
            await update.message.reply_text("✅ Perfeito! Fico feliz em ajudar 😄")
            context.user_data.clear()
            return
        else:
            await criar_ticket(update, user, context.user_data.get("ultima_mensagem"))
            context.user_data.clear()
            return

    # 🔹 Tenta resposta automática
    resposta = responder_automatico(text)

    if resposta:
        await update.message.reply_text(
            f"🤖 Sugestão automática:\n\n{resposta}\n\nIsso resolveu? (sim/não)"
        )
        context.user_data["aguardando_confirmacao"] = True
        context.user_data["ultima_mensagem"] = text
    else:
        await criar_ticket(update, user, text)


# 🎟️ Criar ticket
async def criar_ticket(update: Update, user, text):
    try:
        response = requests.post(
            "http://helpdesk-api:5000/ticket",
            json={"user": user, "description": text}
        )

        data = response.json()

        await update.message.reply_text(
            f"🎟️ Chamado #{data['id']} criado com sucesso!\nNossa equipe irá te ajudar em breve."
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Erro ao criar chamado. Tente novamente mais tarde."
        )
        print(e)


# 🚀 Inicialização
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()