from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv, find_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import requests
import os

load_dotenv(find_dotenv())

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv(
    "API_URL",
    "http://helpdesk-api:5000"
).rstrip("/")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def normalize_admin_values(value):
    if not value:
        return []

    values = []
    for candidate in value.replace("\n", ",").split(","):
        candidate = candidate.strip().strip('"').strip("'")
        if candidate:
            values.append(candidate)
    return values


def get_admin_ids():
    raw = os.getenv("ADMIN_IDS", "")

    candidates = [
        "TELEGRAM_ADMIN_ID",
        "TELEGRAM_ADMIN_IDS",
        "telegram-admin-id",
        "telegram-admin-ids",
        "telegram_admin_id",
        "telegram_admin_ids",
        "ADMIN_CHAT_ID",
        "TELEGRAM_CHAT_ID",
    ]

    values = [raw]
    for key in candidates:
        value = os.environ.get(key)
        if value:
            values.append(value)

    if len(values) == 1 or not any(values[1:]):
        lower_map = {k.lower(): v for k, v in os.environ.items()}
        for key in candidates:
            lowered = key.lower()
            if lowered in lower_map:
                values.append(lower_map[lowered])
                break

    ids = []
    for value in values:
        ids.extend(normalize_admin_values(value))

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
        "1 - Listar chamados (todos)\n"
        "2 - Abrir chamado\n"
        "3 - Consultar / gerenciar chamado\n"
        "4 - /help\n\n"
        "Aliases úteis: /all, /entrar, /encerrar.\n"
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

    if hasattr(update, "message") and update.message:
        from_user = getattr(update.message, "from_user", None)
        if from_user:
            return str(getattr(from_user, "id", ""))

    return ""


def get_chat_id(update):
    if hasattr(update, "effective_chat") and update.effective_chat:
        return str(getattr(update.effective_chat, "id", ""))

    if hasattr(update, "message") and update.message:
        chat = getattr(update.message, "chat", None)
        if chat:
            return str(getattr(chat, "id", ""))

    return get_user_id(update)


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
    context = context or {}

    payload = {
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

    if context.get("chat_id"):
        payload["chat_id"] = context["chat_id"]

    return payload


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


def buscar_ticket_por_id(ticket_id, request_func=None):
    request_func = request_func or requests.get
    try:
        tickets = listar_tickets(request_func=request_func)
        for ticket in tickets:
            if str(ticket.get("id")) == str(ticket_id):
                return ticket
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

        status_code = getattr(response, "status_code", None)
        body = None
        if response and hasattr(response, "json"):
            try:
                body = response.json()
            except Exception:
                body = None

        return {
            "ok": status_code == 200,
            "status_code": status_code,
            "body": body,
        }

    except Exception:
        return {"ok": False, "status_code": None, "body": None}


# =========================
# ADMIN FUNCTIONS (visão completa - todos os chamados)
# =========================
async def mostrar_filtros_listagem(update, context):
    keyboard = [
        ["Abertos"],
        ["Em andamento"],
        ["Encerrados"],
        ["Todos"],
        ["↩️ Voltar"],
    ]
    await update.message.reply_text(
        "Selecione o filtro de chamados:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    context.user_data["step"] = "listar_filtro"


async def listar_chamados_status_admin(update, context, status=None):
    try:
        tickets = listar_tickets()
        if status and status != "todos":
            tickets = [t for t in tickets if t.get("status") == status]

        if not tickets:
            await update.message.reply_text("Nenhum ticket encontrado para esse filtro.")
            return

        msg = f"📋 Chamados ({status or 'todos'}):\n\n"
        keyboard = []

        for t in tickets:
            msg += f"🎫 {t['code']} | {t['user']} | {t['status']}\n"
            keyboard.append([f"📄 Ver {t['code']}"])

        keyboard.append(["↩️ Voltar"])
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        context.user_data["step"] = "listar_detalhes"
    except Exception:
        await update.message.reply_text("Erro ao listar tickets.")


async def consultar_ticket_admin(update, context, ticket_code):
    try:
        response = requests.get(f"{API_URL}/ticket/{ticket_code}")
        if response.status_code == 200:
            ticket = response.json()

            context.user_data["ticket_atual"] = ticket
            context.user_data["step"] = "gerenciar_ticket"

            status_options = ["🔓 Aberto", "⏳ Em atendimento", "✅ Encerrado", "🔄 Reabrir chamado"]
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

    if "reabrir" in text.lower() or ("aberto" in text.lower() and "encerrado" not in text.lower()):
        await alterar_status_ticket(update, context, ticket["id"], "aberto")
    elif "em atendimento" in text.lower():
        await alterar_status_ticket(update, context, ticket["id"], "em atendimento")
    elif "encerrado" in text.lower() or "fechar" in text.lower() or "encerrar" in text.lower():
        await alterar_status_ticket(update, context, ticket["id"], "encerrado")
    elif "adicionar observação" in text.lower() or "observação" in text.lower() or "observacao" in text.lower():
        context.user_data["step"] = "adicionar_observacao"
        await update.message.reply_text("Digite a observação:")
    elif "voltar" in text.lower():
        await mostrar_menu_admin(update, context, "O que você gostaria de fazer?\n\n" + help_admin_text())
    else:
        await update.message.reply_text("Opção inválida.")


async def alterar_status_ticket(update, context, ticket_id, status):
    try:
        response = requests.patch(
            f"{API_URL}/ticket/{ticket_id}/status",
            json={"status": status, "admin": get_user_id(update)}
        )
        if response.status_code == 200:
            ticket = context.user_data.get("ticket_atual")
            if ticket:
                ticket["status"] = status
            if status == "encerrado" and ticket:
                notificar_cliente_fechamento(ticket)
            await update.message.reply_text(f"Status alterado para: {status}")
            await consultar_ticket_admin(update, context, context.user_data["ticket_atual"]["code"])
        else:
            erro_detalhe = ""
            try:
                erro_detalhe = response.json().get("error", "")
            except Exception:
                pass
            await update.message.reply_text(
                f"❌ Erro ao alterar status (HTTP {response.status_code}). {erro_detalhe}"
            )
    except Exception as e:
        await update.message.reply_text(f"Erro ao alterar status: {e}")


async def adicionar_observacao_admin(update, context, observacao):
    ticket = context.user_data.get("ticket_atual")
    if not ticket:
        await update.message.reply_text("Erro: ticket não encontrado.")
        return

    try:
        response = requests.post(
            f"{API_URL}/ticket/{ticket['id']}/note",
            json={"note": observacao, "admin": get_user_id(update), "author_label": "Suporte"}
        )
        if response.status_code == 200:
            await update.message.reply_text("Observação adicionada.")
            await consultar_ticket_admin(update, context, ticket["code"])
        else:
            erro_detalhe = ""
            try:
                erro_detalhe = response.json().get("error", "")
            except Exception:
                pass
            await update.message.reply_text(
                f"❌ Erro ao adicionar observação (HTTP {response.status_code}). {erro_detalhe}"
            )
    except Exception as e:
        await update.message.reply_text(f"Erro ao adicionar observação: {e}")


# =========================
# USUÁRIO COMUM - meus chamados
# =========================
async def listar_meus_chamados(update, context):
    try:
        chat_id = get_chat_id(update)
        tickets = listar_tickets()
        meus = [t for t in tickets if str(t.get("chat_id")) == str(chat_id)]

        if not meus:
            await update.message.reply_text(
                "Você ainda não possui chamados.\n"
                "Use /start para descrever um problema e abrir um chamado."
            )
            context.user_data["step"] = None
            return

        msg = "📋 Seus chamados:\n\n"
        keyboard = []

        for t in meus:
            msg += f"🎫 {t['code']} | {t['status']}\n"
            keyboard.append([f"📄 Ver {t['code']}"])

        keyboard.append(["↩️ Voltar"])

        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        context.user_data["step"] = "meu_listar_detalhes"
    except Exception:
        await update.message.reply_text("Erro ao listar seus chamados.")


async def consultar_ticket_usuario(update, context, ticket_code):
    try:
        response = requests.get(f"{API_URL}/ticket/{ticket_code}")
        if response.status_code != 200:
            await update.message.reply_text("Ticket não encontrado.")
            return

        ticket = response.json()
        chat_id = get_chat_id(update)

        if str(ticket.get("chat_id")) != str(chat_id):
            await update.message.reply_text("Esse chamado não pertence a você.")
            return

        context.user_data["meu_ticket_atual"] = ticket
        context.user_data["step"] = "meu_ticket_detalhe"

        msg = (
            f"🎫 Ticket: {ticket['code']}\n"
            f"📋 Status: {ticket['status']}\n"
            f"📅 Criado: {ticket.get('created_at', 'N/A')}\n\n"
            f"Descrição: {ticket.get('description', 'N/A')}"
        )
        if ticket.get("admin_notes"):
            msg += f"\n\n📝 Observações:\n{ticket['admin_notes']}"

        keyboard = [["📝 Adicionar observação"], ["↩️ Voltar"]]
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
    except Exception:
        await update.message.reply_text("Erro ao consultar ticket.")


async def adicionar_observacao_usuario(update, context, observacao):
    ticket = context.user_data.get("meu_ticket_atual")
    if not ticket:
        await update.message.reply_text("Erro: ticket não encontrado.")
        return

    try:
        response = requests.post(
            f"{API_URL}/ticket/{ticket['id']}/note",
            json={
                "chat_id": get_chat_id(update),
                "note": observacao,
                "author_label": get_user(update),
            }
        )
        if response.status_code == 200:
            await update.message.reply_text("Observação adicionada.")
            await consultar_ticket_usuario(update, context, ticket["code"])
        else:
            await update.message.reply_text("Erro ao adicionar observação.")
    except Exception:
        await update.message.reply_text("Erro ao adicionar observação.")


# =========================
# NOTIFICAÇÃO
# =========================
def notificar_telegram(user, ticket_code, summary=None, request_func=None):
    request_func = request_func or requests.post

    texto_resumo = summary or "Sem descrição adicional"
    texto_resumo = texto_resumo.strip()
    if len(texto_resumo) > 120:
        texto_resumo = texto_resumo[:117].rstrip() + "..."

    targets = []
    if TELEGRAM_CHAT_ID:
        targets.append(TELEGRAM_CHAT_ID)

    for admin_id in get_admin_ids():
        if admin_id and admin_id not in targets:
            targets.append(admin_id)

    print(f"[BOT] notificar_telegram chamada | targets={targets} | TOKEN configurado={bool(TOKEN)}")

    if not targets:
        print("[BOT] notificar_telegram: nenhum target encontrado, notificação não enviada.")
        return None

    if not TOKEN:
        print("[BOT] notificar_telegram: TELEGRAM_TOKEN não configurado, notificação não enviada.")
        return None

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        text = (
            f"🚨 Novo chamado aberto!\n"
            f"🎟️ {ticket_code}\n"
            f"👤 {user}\n"
            f"📌 {texto_resumo}"
        )

        for target in targets:
            payload = {
                "chat_id": target,
                "text": text,
            }
            try:
                resp = request_func(url, json=payload, timeout=5)
            except TypeError:
                resp = request_func(url, json=payload)

            status_code = getattr(resp, "status_code", "desconhecido")
            print(f"[BOT] notificar_telegram: enviado para {target} | status={status_code}")

            if hasattr(resp, "json"):
                try:
                    resp_body = resp.json()
                    if not resp_body.get("ok", True):
                        print(f"[BOT] notificar_telegram: Telegram retornou erro para {target}: {resp_body}")
                except Exception:
                    pass

        return True
    except Exception as e:
        print(f"[BOT] notificar_telegram: EXCEPTION: {e}")
        return None


def notificar_cliente_fechamento(ticket, request_func=None):
    request_func = request_func or requests.post
    chat_id = ticket.get("chat_id")
    if not chat_id:
        print(f"[BOT] notificar_cliente_fechamento: ticket sem chat_id, notificação não enviada. ticket={ticket.get('code')}")
        return None

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        text = (
            f"✅ Seu chamado {ticket.get('code', '')} foi encerrado.\n"
            f"👤 Usuário: {ticket.get('user', '')}\n"
            f"📌 Status: {ticket.get('status', '')}\n"
        )
        if ticket.get("admin_notes"):
            notes = ticket["admin_notes"].strip()
            if notes:
                text += f"\n📝 Observações do atendimento:\n{notes}"

        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        try:
            resp = request_func(url, json=payload, timeout=5)
        except TypeError:
            resp = request_func(url, json=payload)

        status_code = getattr(resp, "status_code", "desconhecido")
        print(f"[BOT] notificar_cliente_fechamento: enviado para {chat_id} | status={status_code}")

        return True
    except Exception as e:
        print(f"[BOT] notificar_cliente_fechamento: EXCEPTION: {e}")
        return None


# =========================
# CRIAR TICKET
# =========================

async def criar_ticket(update, user, context):
    try:
        if "chat_id" not in context:
            context["chat_id"] = get_chat_id(update)

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
                "- /listar para ver seus próprios chamados\n"
                "- /all para listar todos os chamados\n"
                "- /entrar para atender algum chamado\n"
                "- /encerrar para encerrar um chamado\n"
                "- /help para ver o menu de administração\n",
                reply_markup=ReplyKeyboardRemove(),
            )
            await mostrar_menu_admin(update, context)
            return
        else:
            msg = (
                f"Bem-vindo {user_name}! Sou o assistente do Helpdesk.\n\n"
                "Descreva o problema que está acontecendo e eu tento ajudar rapidamente.\n"
                "Ou use /listar para ver seus chamados já abertos."
            )
            await update.message.reply_text(
                msg,
                reply_markup=ReplyKeyboardRemove(),
            )
            context.user_data["step"] = "descricao"

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if is_admin(update):
            await mostrar_menu_admin(update, context, help_admin_text())
            return
        await update.message.reply_text(
            "💡 Comandos disponíveis:\n"
            "/start - reiniciar o atendimento\n"
            "/listar - ver seus chamados\n"
            "/help - mostrar ajuda"
        )

    async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /listar é para todo mundo: cada pessoa vê só os seus
        próprios chamados, filtrados pelo chat_id de quem está
        falando com o bot.
        """
        await listar_meus_chamados(update, context)

    async def all_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /all é restrito ao admin: mostra todos os chamados, com
        filtros por status.
        """
        if not is_admin(update):
            await update.message.reply_text(
                "❌ Acesso negado. Você não está configurado como admin. "
                "Use /debug para ver seu ID e os admins configurados."
            )
            return

        await mostrar_filtros_listagem(update, context)

    async def entrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text(
                "❌ Acesso negado. Você não está configurado como admin. "
                "Use /debug para ver seu ID e os admins configurados."
            )
            return

        if context.args:
            ticket_ref = context.args[0].strip()
            ticket_code = ticket_ref.upper()
            if ticket_ref.isdigit():
                ticket_data = buscar_ticket_por_id(ticket_ref)
                if ticket_data and ticket_data.get("code"):
                    ticket_code = ticket_data["code"]
                else:
                    await update.message.reply_text("Ticket não encontrado.")
                    return
            await consultar_ticket_admin(update, context, ticket_code)
            return

        context.user_data["step"] = "consultar_ticket"
        await update.message.reply_text("Digite o código do chamado (ex: TK2026001):")

    async def encerrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Comando único e padronizado em português para encerrar chamados.
        Substitui os antigos /close e /fechar.
        """
        if not is_admin(update):
            await update.message.reply_text("❌ Acesso negado.")
            return

        if not context.args:
            await update.message.reply_text("Use: /encerrar <id|codigo>")
            return

        ticket_ref = context.args[0].strip()
        ticket_id = ticket_ref
        ticket_data = None

        if ticket_ref.isdigit():
            ticket_data = buscar_ticket_por_id(ticket_ref)
            if ticket_data and ticket_data.get("id"):
                ticket_id = str(ticket_data["id"])
            else:
                await update.message.reply_text("Ticket não encontrado.")
                return
        else:
            ticket_data = buscar_ticket_por_codigo(ticket_ref)
            if ticket_data and ticket_data.get("id"):
                ticket_id = str(ticket_data["id"])
            else:
                await update.message.reply_text("Ticket não encontrado.")
                return

        resultado = fechar_ticket(ticket_id, get_user_id(update))

        if not resultado.get("ok"):
            erro_detalhe = ""
            if resultado.get("body") and isinstance(resultado["body"], dict):
                erro_detalhe = resultado["body"].get("error", "")
            await update.message.reply_text(
                f"❌ Erro ao encerrar ticket (HTTP {resultado.get('status_code')}). {erro_detalhe}\n"
                "Verifique se seu ID está autorizado na API (variável ADMIN_IDS/TELEGRAM_CHAT_ID)."
            )
            return

        if ticket_data:
            notificar_cliente_fechamento(ticket_data)

        await update.message.reply_text(f"✅ Ticket {ticket_ref} encerrado.")

    async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = get_user_id(update)
        admin_ids = get_admin_ids()
        is_admin_flag = is_admin(update)

        msg = f"🔍 **Debug Info**\n\n"
        msg += f"👤 Seu ID: `{user_id}`\n"
        msg += f"🔑 IDs de admin configurados: `{', '.join(admin_ids) if admin_ids else 'nenhum'}`\n"
        msg += f"📌 TELEGRAM_CHAT_ID: `{os.getenv('TELEGRAM_CHAT_ID', '') or 'não configurado'}`\n"
        msg += f"📌 ADMIN_CHAT_ID: `{os.getenv('ADMIN_CHAT_ID', '') or 'não configurado'}`\n"
        msg += f"✅ Você é admin? {is_admin_flag}\n\n"
        msg += (
            "Se você deveria ser admin, copie seu ID e configure uma das variáveis de ambiente:\n"
            "`ADMIN_IDS`, `TELEGRAM_ADMIN_ID`, `telegram-admin-id`, `ADMIN_CHAT_ID` ou `TELEGRAM_CHAT_ID`.\n"
        )

        await update.message.reply_text(msg)

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text or ""
        step = context.user_data.get("step", "tipo")

        user = get_user(update)

        # =========================
        # FLUXO ADMIN
        # =========================
        if step == "admin_menu":
            text_lower = text.lower()

            if text_lower in ("1", "1 - listar chamados", "listar chamados", "listar"):
                await mostrar_filtros_listagem(update, context)
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

        if step == "listar_filtro":
            status = None
            text_lower = text.lower()
            if "aberto" in text_lower:
                status = "aberto"
            elif "em andamento" in text_lower or "andamento" in text_lower:
                status = "em atendimento"
            elif "encerr" in text_lower:
                status = "encerrado"
            elif "todos" in text_lower:
                status = "todos"
            elif "voltar" in text_lower:
                await mostrar_menu_admin(update, context, "O que você gostaria de fazer?\n\n" + help_admin_text())
                return

            if status is None:
                await update.message.reply_text(
                    "Escolha um filtro válido: Abertos, Em andamento, Encerrados ou Todos."
                )
                return

            await listar_chamados_status_admin(update, context, status)
            return

        if step == "gerenciar_ticket":
            await gerenciar_ticket_admin(update, context, text)
            return

        if step == "adicionar_observacao":
            await adicionar_observacao_admin(update, context, text)
            return

        # =========================
        # FLUXO USUÁRIO - meus chamados
        # =========================
        if step == "meu_listar_detalhes":
            if text.startswith("📄 Ver "):
                ticket_code = text.replace("📄 Ver ", "").strip()
                await consultar_ticket_usuario(update, context, ticket_code)
            elif "voltar" in text.lower():
                await update.message.reply_text(
                    "Ok! Digite /start para voltar ao início.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                context.user_data["step"] = None
            return

        if step == "meu_ticket_detalhe":
            text_lower = text.lower()
            if "adicionar observação" in text_lower or "observação" in text_lower or "observacao" in text_lower:
                context.user_data["step"] = "usuario_adicionar_observacao"
                await update.message.reply_text("Digite sua observação:")
                return
            if "voltar" in text_lower:
                await listar_meus_chamados(update, context)
                return
            await update.message.reply_text("Opção inválida.")
            return

        if step == "usuario_adicionar_observacao":
            await adicionar_observacao_usuario(update, context, text)
            return

        # =========================
        # FLUXO ABERTURA DE CHAMADO (todos)
        # =========================

        # Compatibilidade com testes antigos: passo 'tipo' existe mas redireciona direto para 'descricao'
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

            await update.message.reply_text(
                context.user_data["sugestao"]
            )

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
                await update.message.reply_text(
                    "✅ Ótimo! Fico feliz que conseguimos resolver!\n\n"
                    "Digite /start quando precisar de algo novamente.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                context.user_data["step"] = "finalizado"
                return

            if "ainda não funcionou" in text.lower() or "não funcionou" in text.lower():
                await criar_ticket(
                    update,
                    user,
                    context.user_data
                )
                await update.message.reply_text(
                    "Entendido! Abrimos um chamado para nossa equipe analisar.\n\n"
                    "Digite /start quando precisar de algo novamente.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                context.user_data["step"] = "finalizado"
                return

            if "nova descrição" in text.lower():
                context.user_data.clear()
                context.user_data["step"] = "descricao"
                await update.message.reply_text(
                    "Descreva o novo problema:"
                )
                return

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
    app.add_handler(CommandHandler("debug", debug_command))
    app.add_handler(CommandHandler(["lista", "listar"], listar))
    app.add_handler(CommandHandler("all", all_tickets))
    app.add_handler(CommandHandler("entrar", entrar))
    app.add_handler(CommandHandler("encerrar", encerrar))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    return app


if __name__ == "__main__":
    app = run_bot()
    app.run_polling()