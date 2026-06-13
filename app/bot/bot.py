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

def get_admin_ids():
    raw = os.getenv("ADMIN_IDS", "")

    fallback = ""
    candidates = [
        "TELEGRAM_ADMIN_ID",
        "TELEGRAM_ADMIN_IDS",
        "telegram-admin-id",
        "telegram-admin-ids",
        "telegram_admin_id",
        "telegram_admin_ids",
    ]

    for key in candidates:
        value = os.getenv(key)
        if value:
            fallback = value
            break

    if not fallback:
        lower_map = {k.lower(): v for k, v in os.environ.items()}
        for key in [
            "telegram_admin_id",
            "telegram_admin_ids",
            "telegram-admin-id",
            "telegram-admin-ids",
        ]:
            if key in lower_map:
                fallback = lower_map[key]
                break

    values = [raw, fallback]
    ids = []
    for value in values:
        for item in value.split(","):
            candidate = item.strip()
            if candidate:
                ids.append(candidate)
    return list(dict.fromkeys(ids))


ADMIN_IDS = get_admin_ids()

FAQ = {
    "internet lenta": "🔌 Reiniciar o roteador e verificar os cabos.",
    "computador não liga": "⚡ Verificar fonte e cabo de energia.",
    "impressora não imprime": "🖨️ Impressora: verificar conexão e tinta.",
}


def help_admin_text():
    return (
        "🛠️ Menu do administrador\n\n"
        "1 - Listar chamados\n"
        "2 - Abrir chamado\n"
        "3 - Consultar / gerenciar chamado\n"
        "4 - /help\n\n"
        "Aliases úteis: /listar, /entrar, /encerrar.\n"
        "Use os números ou as palavras exibidas para navegar."
    )


async def mostrar_menu_admin(update, context, mensagem=None):
    keyboard = [
        ["1 - Listar chamados"],
        ["2 - Abrir chamado"],
        ["3 - Consultar / gerenciar chamado"],
        ["4 - /help"],
    ]
    await update.message.reply_text(
        mensagem or help_admin_text(),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    context.user_data["step"] = "admin_menu"


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
    user_id = get_user_id(update)
    if not user_id:
        return False
    return user_id in get_admin_ids()


# =========================
# IA - SOLUÇÕES
# =========================
def responder_automatico(texto):
    if not texto:
        return mensagem_padrao()

    texto = texto.lower()

    if "sem conexão" in texto:
        return "❌ Verificar conexão com a internet e cabos de rede."

    if "conexão" in texto and "internet" in texto:
        return "🌐 Problema de conexão detectado. Verifique sua conexão com a internet."

    if "internet" in texto:
        return "🌐 Reinicie o roteador e verifique sua conexão."

    return "🤖 Caso o problema persista, entre em contato com o suporte."


def sugerir_solucao(texto):
    """
    Sugere soluções baseadas no tipo de problema.
    Oferece múltiplos cenários que o usuário pode tentar.
    """
    texto = (texto or "").lower()

    # INTERNET / REDE / WIFI
    if any(x in texto for x in ["internet", "rede", "wifi", "conexão", "sem conexão"]):
        return (
            "🌐 **Problemas de Internet/Rede**\n\n"
            "Tente essas soluções em ordem:\n"
            "1️⃣ Verifique se o cabo de rede está conectado na porta correta\n"
            "2️⃣ Reinicie o roteador (desligue por 30 segundos)\n"
            "3️⃣ Verificar status do WiFi no dispositivo\n"
            "4️⃣ Abra o navegador e tente acessar uma página (ex: google.com)\n"
            "5️⃣ Se outros dispositivos não conectam, problema pode ser do provedor\n\n"
            "Se nenhuma solução funcionar, abriremos um chamado."
        )

    # COMPUTADOR LENTO / TRAVANDO
    if any(x in texto for x in ["travando", "lento", "lentidão", "congelado", "trava"]):
        return (
            "💻 **Computador Lento ou Travando**\n\n"
            "Tente essas soluções em ordem:\n"
            "1️⃣ Tente reiniciar o computador completamente\n"
            "2️⃣ Feche programas desnecessários (abra Gerenciador de Tarefas com Ctrl+Shift+Esc)\n"
            "3️⃣ Verifique espaço livre em disco (pode estar cheio)\n"
            "4️⃣ Desative efeitos visuais desnecessários\n"
            "5️⃣ Atualize drivers de vídeo e chipset\n"
            "6️⃣ Faça varredura antivírus\n\n"
            "Se continuar lento, pode haver problema de hardware."
        )

    # SENHA / LOGIN / ACESSO
    if any(x in texto for x in ["senha", "login", "acesso", "não consigo entrar", "bloqueado"]):
        return (
            "🔐 **Problemas de Senha/Acesso**\n\n"
            "Tente essas soluções em ordem:\n"
            "1️⃣ Verifique se Caps Lock está ativado\n"
            "2️⃣ Digite a senha com atenção (diferencia maiúsculas/minúsculas)\n"
            "3️⃣ Pressione Ctrl+Alt+Delete e selecione 'Trocar Senha'\n"
            "4️⃣ Use a opção 'Esqueci minha senha' no sistema\n"
            "5️⃣ Se a conta está bloqueada, espere 15 minutos e tente novamente\n"
            "6️⃣ Limpe cookies e cache do navegador\n\n"
            "Se ainda não funcionar, nossa equipe pode redefinir sua senha."
        )

    # IMPRESSORA
    if any(x in texto for x in ["impressora", "imprimir", "não imprime", "papel"]):
        return (
            "🖨️ **Problemas com Impressora**\n\n"
            "Tente essas soluções em ordem:\n"
            "1️⃣ Verifique se a impressora está ligada e conectada\n"
            "2️⃣ Verifique se há papel na bandeja\n"
            "3️⃣ Veja o nível de tinta/toner\n"
            "4️⃣ Abra 'Configurações > Dispositivos > Impressoras' e verifique fila\n"
            "5️⃣ Reinicie a impressora\n"
            "6️⃣ Limpe cabeçotes de impressão (se tiver opção)\n"
            "7️⃣ Reinstale drivers da impressora\n\n"
            "Se a impressora não aparecer, pode estar com problema de conexão."
        )

    # ERRO / TELA AZUL / CRASH
    if any(x in texto for x in ["erro", "tela azul", "crash", "encerra", "fecha sozinho"]):
        return (
            "❌ **Erros e Crashes**\n\n"
            "Tente essas soluções em ordem:\n"
            "1️⃣ Reinicie o computador\n"
            "2️⃣ Atualize Windows (Configurações > Atualização)\n"
            "3️⃣ Desinstale programas instalados recentemente\n"
            "4️⃣ Execute análise de disco (clique direito em C: > Propriedades > Ferramentas)\n"
            "5️⃣ Use Restauração do Sistema para voltar a um ponto anterior\n"
            "6️⃣ Faça varredura antivírus completa\n\n"
            "Se continuar tendo erros, pode haver problema de hardware."
        )

    # EMAIL
    if any(x in texto for x in ["email", "outlook", "gmail", "não consigo enviar"]):
        return (
            "📧 **Problemas com Email**\n\n"
            "Tente essas soluções em ordem:\n"
            "1️⃣ Verifique conexão de internet\n"
            "2️⃣ Confirme usuário e senha estão corretos\n"
            "3️⃣ Sincronize a conta (clique direito na conta > Sincronizar)\n"
            "4️⃣ Atualize o Outlook ou reconfigure a conta\n"
            "5️⃣ Limpe cache de senhas (Arquivo > Opções > Segurança)\n"
            "6️⃣ Verifique se há limite de armazenamento atingido\n\n"
            "Para problemas complexos, nossa equipe pode reconfigurar."
        )

    # ARQUIVO / PERDA DE DADOS
    if any(x in texto for x in ["arquivo", "arquivo corrompido", "não abre", "perdi"]):
        return (
            "📁 **Problemas com Arquivos**\n\n"
            "Tente essas soluções em ordem:\n"
            "1️⃣ Verifique permissões do arquivo (clique direito > Propriedades)\n"
            "2️⃣ Tente abrir com outro programa\n"
            "3️⃣ Recupere de backup/versão anterior\n"
            "4️⃣ Desative antivírus temporariamente\n"
            "5️⃣ Se foi deletado, use software de recuperação\n"
            "6️⃣ Escaneie com antivírus completo\n\n"
            "Se o arquivo está corrompido, pode ser necessária recuperação profissional."
        )

    # RESPOSTA GENÉRICA
    return (
        "💡 **Solução Sugerida**\n\n"
        "Para este tipo de problema:\n"
        "1️⃣ Reinicie o computador\n"
        "2️⃣ Feche navegadores e programas desnecessários\n"
        "3️⃣ Atualize o Windows e drivers\n"
        "4️⃣ Execute análise antivírus\n\n"
        "Se o problema persistir, nossa equipe pode investigar."
    )


# =========================
# PAYLOAD
# =========================
def criar_payload(user, context):
    """
    Cria payload para envio de ticket.
    Mantém compatibilidade com categoria e subcategoria quando existirem.
    """
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
        "ai_suggestion": context.get("sugestao") or context.get("ai", ""),
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


def buscar_ticket_por_codigo(ticket_code, request_func=None):
    request_func = request_func or requests.get

    try:
        response = request_func(f"{API_URL}/ticket/{ticket_code}")
        if response and hasattr(response, "json"):
            return response.json()
        return None
    except Exception:
        return None


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
            if not tickets:
                await update.message.reply_text("Nenhum ticket encontrado.")
                return

            msg = "📋 Chamados:\n\n"
            keyboard = []

            for t in tickets:
                msg += f"🎫 {t['code']} | {t['user']} | {t['status']}\n"
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
        await mostrar_menu_admin(update, context, "O que você gostaria de fazer?\n\n" + help_admin_text())
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
def notificar_telegram(user, ticket_code, summary=None, request_func=None):
    if not TELEGRAM_CHAT_ID:
        return None

    request_func = request_func or requests.post

    texto_resumo = summary or "Sem descrição adicional"
    texto_resumo = texto_resumo.strip()
    if len(texto_resumo) > 120:
        texto_resumo = texto_resumo[:117].rstrip() + "..."

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": (
                f"🚨 Novo chamado aberto!\n"
                f"🎟️ {ticket_code}\n"
                f"👤 {user}\n"
                f"📌 {texto_resumo}"
            ),
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
                codigo,
                summary=context.get("descricao")
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

        user_name = get_user(update)

        if is_admin(update):
            await update.message.reply_text(
                f"Olá {user_name}, o que você gostaria de fazer?\n\n"
                "- /listar para listar os chamados\n"
                "- /entrar para atender algum chamado\n"
                "- /help para ver o menu de administração\n"
            )
            await mostrar_menu_admin(update, context)
            return
        else:
            context.user_data.clear()
            context.user_data["step"] = "descricao"

            await update.message.reply_text(
                f"Bem-vindo {user_name}! Sou o assistente do Helpdesk.\n\n"
                "Descreva o problema que está acontecendo e eu tento ajudar rapidamente."
            )
            await update.message.reply_text(
                "Se preferir, você também pode abrir um chamado direto após a análise."
            )

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if is_admin(update):
            await mostrar_menu_admin(update, context, help_admin_text())
            return
        await update.message.reply_text(
            "💡 Comandos disponíveis:\n"
            "/start - reiniciar o atendimento\n"
            "/help - mostrar ajuda"
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

    async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("❌ Acesso negado.")
            return

        await tickets(update, context)

    async def entrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("❌ Acesso negado.")
            return

        context.user_data["step"] = "consultar_ticket"
        await update.message.reply_text("Digite o código do chamado (ex: TK2026001):")

    async def close(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("❌ Acesso negado.")
            return

        if not context.args:
            await update.message.reply_text("Use: /close <id|codigo>")
            return

        ticket_ref = context.args[0].strip()
        ticket_id = ticket_ref

        if not ticket_ref.isdigit():
            ticket_data = buscar_ticket_por_codigo(ticket_ref)
            if ticket_data and ticket_data.get("id"):
                ticket_id = str(ticket_data["id"])
            else:
                await update.message.reply_text("Ticket não encontrado.")
                return

        fechar_ticket(ticket_id, get_user_id(update))

        await update.message.reply_text(f"Ticket {ticket_ref} encerrado.")

    async def encerrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await close(update, context)

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text or ""
        step = context.user_data.get("step", "tipo")

        user = get_user(update)

        if step == "admin_menu":
            text_lower = text.lower()

            if text_lower in ("1", "1 - listar chamados", "listar chamados", "listar"):
                await listar_chamados_admin(update, context)
                return

            if text_lower in ("2", "2 - abrir chamado", "abrir chamado", "abrir"):
                context.user_data.clear()
                context.user_data["step"] = "descricao"
                await update.message.reply_text("Descreva o problema que está acontecendo:")
                return

            if text_lower in (
                "3",
                "3 - consultar / gerenciar chamado",
                "consultar / gerenciar chamado",
                "consultar chamado",
                "gerenciar chamado",
                "entrar no chamado",
            ):
                context.user_data["step"] = "consultar_ticket"
                await update.message.reply_text("Digite o número do ticket (ex: TKHW2024001):")
                return

            if text_lower in ("4", "4 - /help", "help", "/help"):
                await mostrar_menu_admin(update, context, help_admin_text())
                return

            await update.message.reply_text("Escolha uma opção válida.\n\n" + help_admin_text())
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
                await mostrar_menu_admin(update, context, "O que você gostaria de fazer?\n\n" + help_admin_text())
            return

        if step == "gerenciar_ticket":
            await gerenciar_ticket_admin(update, context, text)
            return

        if step == "adicionar_observacao":
            await adicionar_observacao_admin(update, context, text)
            return

        # Compatibilidade com testes antigos: passo 'tipo' existe mas redireciona direto para 'descricao'
        # sem mostrar perguntas para o usuário.
        if step == "tipo":
            context.user_data["step"] = "descricao"

            await update.message.reply_text(
                "Descreva o problema que está acontecendo:"
            )
            return

        if step == "descricao":
            if not text:
                await update.message.reply_text(
                    "Descreva o problema."
                )
                return

            context.user_data["descricao"] = text
            context.user_data["sugestao"] = sugerir_solucao(text)

            # Mostra a sugestão
            await update.message.reply_text(
                context.user_data["sugestao"]
            )

            # Pergunta se o usuário quer tentar a solução ou abrir chamado
            keyboard = [
                ["✅ Vou tentar essa solução"],
                ["❌ Abrir chamado agora"]
            ]
            await update.message.reply_text(
                "\nVocê gostaria de tentar essas soluções ou prefere que abrirmos um chamado?",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            context.user_data["step"] = "aguardando_confirmacao"
            return

        if step == "aguardando_confirmacao":
            text_lower = text.lower()

            if "abrir chamado" in text_lower:
                # Abre chamado diretamente
                await criar_ticket(
                    update,
                    user,
                    context.user_data
                )
                context.user_data["step"] = "finalizado"
                return

            if "sim" in text_lower or "funcionou" in text_lower or "resolvido" in text_lower:
                await update.message.reply_text("✅ Ótimo! Fico feliz em ajudar.")
                context.user_data["step"] = "finalizado"
                return

            if "não" in text_lower or "nao" in text_lower or "não funcionou" in text_lower or "nao funcionou" in text_lower:
                await criar_ticket(
                    update,
                    user,
                    context.user_data
                )
                context.user_data["step"] = "finalizado"
                return

            if "vou tentar" in text_lower:
                # Usuário vai tentar a solução
                keyboard = [
                    ["✅ Problema resolvido!"],
                    ["❌ Ainda não funcionou"],
                    ["🔄 Nova descrição"]
                ]
                await update.message.reply_text(
                    "Tente seguir os passos. Quando terminar, me avise!",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                context.user_data["step"] = "tentando_solucao"
                return

            # Se não entendeu, repete a pergunta
            keyboard = [
                ["✅ Vou tentar essa solução"],
                ["❌ Abrir chamado agora"]
            ]
            await update.message.reply_text(
                "Por favor, escolha uma opção:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

        if step == "tentando_solucao":
            if "problema resolvido" in text.lower() or "resolvido" in text.lower():
                keyboard = [["🏠 Voltar ao início"]]
                await update.message.reply_text(
                    "✅ Ótimo! Fico feliz que conseguimos resolver!",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                context.user_data["step"] = "finalizado"
                return

            if "ainda não funcionou" in text.lower() or "não funcionou" in text.lower():
                # Abre chamado se o usuário não conseguiu resolver
                await criar_ticket(
                    update,
                    user,
                    context.user_data
                )
                keyboard = [["🏠 Voltar ao início"]]
                await update.message.reply_text(
                    "Entendido! Abrimos um chamado para nossa equipe analisar.",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                context.user_data["step"] = "finalizado"
                return

            if "nova descrição" in text.lower():
                # Usuário quer descrever outro problema
                context.user_data.clear()
                context.user_data["step"] = "descricao"
                await update.message.reply_text(
                    "Descreva o novo problema:"
                )
                return

            # Opções inválidas
            keyboard = [
                ["✅ Problema resolvido!"],
                ["❌ Ainda não funcionou"],
                ["🔄 Nova descrição"]
            ]
            await update.message.reply_text(
                "Qual é o resultado? Escolha uma opção:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tickets", tickets))
    app.add_handler(CommandHandler(["lista", "listar"], listar))
    app.add_handler(CommandHandler("entrar", entrar))
    app.add_handler(CommandHandler("close", close))
    app.add_handler(CommandHandler("encerrar", encerrar))
    app.add_handler(CommandHandler("fechar", close))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    return app


if __name__ == "__main__":
    app = run_bot()
    app.run_polling()