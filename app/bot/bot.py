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
API_URL = os.getenv(
    "API_URL",
    "http://helpdesk-api:5000"
).rstrip("/")
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
    return bool(get_user_id(update)) and get_user_id(update) in ADMIN_IDS


# =========================
# IA
# =========================
def sugerir_solucao(texto):
    texto = (texto or "").lower()

    if any(x in texto for x in ["internet", "rede", "wifi", "conexão"]):
        return (
            "🌐 Verifique se o cabo de rede está conectado, "
            "teste reiniciar o roteador e confirme se outros dispositivos acessam a internet."
        )

    if any(x in texto for x in ["travando", "lento", "lentidão"]):
        return "💻 Tente reiniciar o computador e fechar programas desnecessários."

    if any(x in texto for x in ["senha", "login", "acesso"]):
        return (
            "🔐 Verifique usuário e senha e tente novamente."
        )

    if any(x in texto for x in ["impressora", "imprimir"]):
        return (
            "🖨️ Verifique conexão, papel e nível de tinta."
        )

    return (
        "💡 Posso abrir um chamado para que a equipe analise o problema."
    )

def responder_automatico(texto):
    if not texto:
        return mensagem_padrao()

    texto = texto.lower()

    if "sem conexão" in texto:
        return "❌ Verificar conexão com a internet e cabos de rede."

    if "conexão" in texto and "internet" in texto:
        return (
            "🌐 Problema de conexão detectado. "
            "Verifique sua conexão com a internet."
        )

    if "internet" in texto:
        return "🌐 Reinicie o roteador e verifique sua conexão."

    return (
        "🤖 Caso o problema persista, "
        "entre em contato com o suporte."
    )


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
        "category": (
            context.get("categoria")
            or context.get("category")
            or "auto"
        ),
        "subcategory": (
            context.get("dispositivo")
            or context.get("subcategory")
            or ""
        ),
        "ai_suggestion": (
            context.get("sugestao")
            or context.get("ai", "")
        ),
    }


# =========================
# API
# =========================
def enviar_ticket(payload, request_func=None):
    request_func = request_func or requests.post

    try:
        try:
            response = request_func(
                f"{API_URL}/ticket",
                json=payload,
                timeout=5
            )
        except TypeError:
            response = request_func(
                f"{API_URL}/ticket",
                json=payload
            )

        if response and hasattr(response, "json"):
            return response.json()

        return None

    except Exception:
        return None
    
    
# =========================
# API - ADMIN
# =========================

def listar_tickets(request_func=None):
    request_func = request_func or requests.get

    try:
        response = request_func(
            f"{API_URL}/tickets"
        )

        if hasattr(response, "json"):
            return response.json()

        return []

    except Exception:
        return []


def fechar_ticket(ticket_id, admin, request_func=None):
    request_func = request_func or requests.post

    try:
        response = request_func(
            f"{API_URL}/ticket/{ticket_id}/close",
            json={"admin": admin}
        )

        if response and hasattr(response, "json"):
            return response.json()

        return None

    except Exception:
        return None


# =========================
# ADMIN FUNCTIONS
# =========================
async def listar_chamados_admin(update, context):
    try:
        response = requests.get(f"{API_URL}/tickets")
        if response.status_code == 200:
            tickets = response.json()
            tickets_abertos = [t for t in tickets if t.get("status") == "aberto"]

            if not tickets_abertos:
                await update.message.reply_text("Nenhum ticket aberto encontrado.")
                return

            msg = "📋 Tickets abertos:\n\n"
            keyboard = []

            for t in tickets_abertos:
                msg += f"🎫 {t['code']} - {t['user']}\n"
                keyboard.append([f"📄 Ver {t['code']}"])

            keyboard.append(["↩️ Voltar"])
            await update.message.reply_text(
                msg,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            context.user_data["step"] = "listar_detalhes"
        else:
            await update.message.reply_text("Erro ao listar tickets.")
    except Exception:
        await update.message.reply_text("Erro ao listar tickets.")


async def consultar_ticket_admin(update, context, ticket_code):
    try:
        response = requests.get(f"{API_URL}/ticket/{ticket_code}")
        if response.status_code == 200:
            ticket = response.json()

            context.user_data["ticket_atual"] = ticket
            context.user_data["step"] = "gerenciar_ticket"

            status_options = ["🔓 Aberto", "⏳ Em atendimento", "✅ Encerrado"]
            keyboard = [[opt] for opt in status_options]
            keyboard.append(["📝 Adicionar observação"])
            keyboard.append(["↩️ Voltar"])

            msg = f"🎫 Ticket: {ticket['code']}\n👤 Usuário: {ticket['user']}\n📅 Criado: {ticket.get('created_at', 'N/A')}\n📋 Status: {ticket['status']}\n\nDescrição: {ticket.get('description', 'N/A')}"

            if ticket.get('admin_notes'):
                msg += f"\n\n📝 Observações:\n{ticket['admin_notes']}"

            await update.message.reply_text(
                msg,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        elif response.status_code == 404:
            await update.message.reply_text("Ticket não encontrado.")
            context.user_data["step"] = "admin_menu"
        else:
            await update.message.reply_text("Erro ao consultar ticket.")
    except Exception:
        await update.message.reply_text("Erro ao consultar ticket.")


async def gerenciar_ticket_admin(update, context, text):
    ticket = context.user_data.get("ticket_atual")
    if not ticket:
        await update.message.reply_text("Erro: ticket não encontrado.")
        return

    if "aberto" in text.lower():
        await alterar_status_ticket(update, context, ticket["id"], "aberto")
    elif "em atendimento" in text.lower():
        await alterar_status_ticket(update, context, ticket["id"], "em atendimento")
    elif "encerrado" in text.lower():
        await alterar_status_ticket(update, context, ticket["id"], "encerrado")
    elif "adicionar observação" in text.lower():
        context.user_data["step"] = "adicionar_observacao"
        await update.message.reply_text("Digite a observação:")
    elif "voltar" in text.lower():
        context.user_data["step"] = "admin_menu"
        keyboard = [
            ["🆕 Abrir chamado"],
            ["📋 Listar chamados"],
            ["🔍 Consultar chamado"]
        ]
        await update.message.reply_text(
            "O que você gostaria de fazer?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    else:
        await update.message.reply_text("Opção inválida.")


async def alterar_status_ticket(update, context, ticket_id, status):
    try:
        # Assumindo que há um endpoint para alterar status
        response = requests.patch(
            f"{API_URL}/ticket/{ticket_id}/status",
            json={"status": status, "admin": get_user_id(update)}
        )
        if response.status_code == 200:
            await update.message.reply_text(f"Status alterado para: {status}")
            # Recarregar ticket
            await consultar_ticket_admin(update, context, context.user_data["ticket_atual"]["code"])
        else:
            await update.message.reply_text("Erro ao alterar status.")
    except Exception:
        await update.message.reply_text("Erro ao alterar status.")


async def adicionar_observacao_admin(update, context, observacao):
    ticket = context.user_data.get("ticket_atual")
    if not ticket:
        await update.message.reply_text("Erro: ticket não encontrado.")
        return

    try:
        # Assumindo endpoint para adicionar observação
        response = requests.post(
            f"{API_URL}/ticket/{ticket['id']}/note",
            json={"note": observacao, "admin": get_user_id(update)}
        )
        if response.status_code == 200:
            await update.message.reply_text("Observação adicionada.")
            await consultar_ticket_admin(update, context, ticket["code"])
        else:
            await update.message.reply_text("Erro ao adicionar observação.")
    except Exception:
        await update.message.reply_text("Erro ao adicionar observação.")


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

        data = enviar_ticket(payload)

        print(f"[BOT] Resposta API: {data}")

        if data and data.get("id"):

            codigo = (
                data.get("ticket_code")
                or f"TK{str(data['id']).zfill(3)}"
            )

            await update.message.reply_text(
                f"🎟️ Chamado {codigo} criado!"
            )

            notificar_telegram(
                user,
                codigo
            )

        else:

            erro = (
                data.get("error")
                if isinstance(data, dict)
                else "Erro desconhecido"
            )

            await update.message.reply_text(
                f"❌ Erro ao criar chamado: {erro}"
            )

    except Exception as e:
        print(f"[BOT] EXCEPTION: {e}")

        await update.message.reply_text(
            f"❌ Erro interno: {str(e)}"
        )

# =========================
# BOT
# =========================
def run_bot(token=None):
    token = token or TOKEN
    app = ApplicationBuilder().token(token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        context.user_data["step"] = "tipo"

        user_name = get_user(update)

        if is_admin(update):
            keyboard = [
                ["🆕 Abrir chamado"],
                ["📋 Listar chamados"],
                ["🔍 Consultar chamado"]
            ]
            await update.message.reply_text(
                f"Bem-vindo {user_name}, o que você gostaria de fazer?",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            )
            context.user_data["step"] = "admin_menu"
        else:
            await update.message.reply_text(
                f"Bem-vindo {user_name}! Sou o assistente do Helpdesk.\n\nComo posso ajudá-lo hoje?"
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

        if step == "admin_menu":
            if "abrir chamado" in text.lower():
                context.user_data.clear()
                context.user_data["step"] = "descricao"

                await update.message.reply_text(
                    "Descreva o problema que está acontecendo:"
                )
                return

            if "listar chamados" in text.lower():
                await listar_chamados_admin(update, context)
                return

            if "consultar chamado" in text.lower():
                context.user_data["step"] = "consultar_ticket"
                await update.message.reply_text("Digite o número do ticket (ex: TKHW2024001):")
                return

            await update.message.reply_text("Escolha uma opção válida.")
            return

        if step == "consultar_ticket":
            ticket_code = text.strip().upper()
            await consultar_ticket_admin(update, context, ticket_code)
            return

        if step == "listar_detalhes":
            if text.startswith("📄 Ver "):
                ticket_code = text.replace("📄 Ver ", "").strip()
                await consultar_ticket_admin(update, context, ticket_code)
            elif "voltar" in text.lower():
                context.user_data["step"] = "admin_menu"
                keyboard = [
                    ["🆕 Abrir chamado"],
                    ["📋 Listar chamados"],
                    ["🔍 Consultar chamado"]
                ]
                await update.message.reply_text(
                    "O que você gostaria de fazer?",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
            return

        if step == "gerenciar_ticket":
            await gerenciar_ticket_admin(update, context, text)
            return

        if step == "adicionar_observacao":
            await adicionar_observacao_admin(update, context, text)
            return

        if step == "tipo":
            if not text:
                await update.message.reply_text(
                    "Você quer hardware ou software?"
                )
                return

            if "hardware" in text.lower():
                context.user_data["categoria"] = "hardware"
            elif "software" in text.lower():
                context.user_data["categoria"] = "software"
            else:
                await update.message.reply_text(
                    "Escolha hardware ou software."
                )
                return

            context.user_data["step"] = "equipamento"
            await update.message.reply_text(
                "Qual equipamento?"
            )
            return

        if step == "equipamento":
            if not text:
                await update.message.reply_text(
                    "Qual equipamento?"
                )
                return

            context.user_data["dispositivo"] = text
            context.user_data["step"] = "descricao"

            await update.message.reply_text(
                "Descreva o problema."
            )
            return

        if step == "descricao":
            if not text:
                await update.message.reply_text(
                    "Descreva o problema."
                )
                return

            context.user_data["descricao"] = text

            if problema_simples(text):
                await update.message.reply_text(
                    responder_automatico(text)
                )
                await update.message.reply_text(
                    sugerir_solucao(text)
                )
                context.user_data["step"] = "aguardando_confirmacao"
                await update.message.reply_text(
                    "O problema foi resolvido com essa orientação? (sim/não)"
                )
            else:
                await criar_ticket(
                    update,
                    user,
                    context.user_data
                )
                context.user_data["step"] = "finalizado"

            return

        if step == "aguardando_confirmacao":
            if "sim" in text.lower():
                await update.message.reply_text(
                    "✅ Ótimo! Fico feliz em ajudar."
                )
            else:
                await criar_ticket(
                    update,
                    user,
                    context.user_data
                )

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