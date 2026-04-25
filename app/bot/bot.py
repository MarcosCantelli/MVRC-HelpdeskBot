from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

# 🧠 Base simples (IA fake)
FAQ = {
    "internet lenta": "🔌 Reinicie o roteador e verifique os cabos.",
    "computador não liga": "⚡ Verifique fonte e cabo de energia.",
    "impressora não imprime": "🖨️ Verifique conexão e tinta.",
    "filamento": "🧵 Verifique se o filamento não travou.",
}


def responder_automatico(texto):
    texto = texto.lower()
    for chave in FAQ:
        if chave in texto:
            return FAQ[chave]
    return None


# 🚀 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🖥️ Hardware", "💻 Software"]
    ]

    await update.message.reply_text(
        "👋 Bem-vindo ao *Help Desk MVRC*\n\nEscolha uma categoria:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )


# 🎯 Categoria
async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "Hardware" in text:
        context.user_data["category"] = "hardware"

        keyboard = [
            ["🖨️ Problema na impressora"],
            ["🧱 Impressão 3D"]
        ]

        await update.message.reply_text(
            "🔧 Qual tipo de problema?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    elif "Software" in text:
        context.user_data["category"] = "software"
        await update.message.reply_text("💻 Descreva seu problema de software:")


# 🖨️ Submenu Hardware
async def handle_subcategory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "impressora" in text.lower():
        context.user_data["subcategory"] = "impressora"
        await update.message.reply_text("🖨️ Qual o problema da impressora?")

    elif "3d" in text.lower():
        context.user_data["subcategory"] = "impressao_3d"

        keyboard = [
            ["🛠️ Problema na impressora 3D"],
            ["📦 Quero imprimir algo"]
        ]

        await update.message.reply_text(
            "Escolha uma opção:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )


# 🤖 Fluxo principal
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.username or "anonimo"
    text = update.message.text

    # categoria
    if any(x in text for x in ["Hardware", "Software"]):
        await handle_category(update, context)
        return

    # submenu
    if any(x in text.lower() for x in ["impressora", "3d"]):
        await handle_subcategory(update, context)
        return

    # confirmação IA
    if context.user_data.get("aguardando_confirmacao"):
        if text.lower() == "sim":
            await update.message.reply_text("✅ Ótimo! Resolvido 😄")
            context.user_data.clear()
            return
        else:
            await criar_ticket(update, user, context)
            context.user_data.clear()
            return

    # IA
    resposta = responder_automatico(text)

    if resposta:
        await update.message.reply_text(
            f"🤖 Sugestão:\n\n{resposta}\n\nIsso resolveu? (sim/não)"
        )
        context.user_data["aguardando_confirmacao"] = True
        context.user_data["descricao"] = text
        context.user_data["ai"] = resposta
    else:
        context.user_data["descricao"] = text
        await criar_ticket(update, user, context)


# 🎟️ Criar ticket
async def criar_ticket(update: Update, user, context):
    try:
        payload = {
            "user": user,
            "description": context.get("descricao"),
            "category": context.get("category"),
            "subcategory": context.get("subcategory"),
            "ai_suggestion": context.get("ai")
        }

        response = requests.post(
            "http://helpdesk-api:5000/ticket",
            json=payload
        )

        data = response.json()

        await update.message.reply_text(
            f"🎟️ Chamado #{data['id']} criado!\nEquipe irá analisar."
        )

    except Exception as e:
        await update.message.reply_text("❌ Erro ao criar chamado.")
        print(e)


# 🚀 INIT
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()