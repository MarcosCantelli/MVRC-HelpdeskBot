import pytest
from types import SimpleNamespace
from app.bot.bot import run_bot


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.responses = []

    async def reply_text(self, text, reply_markup=None):
        self.responses.append(text)


class FakeUpdate:
    def __init__(self, text=""):
        self.message = FakeMessage(text)


def get_handler(app, name):
    for group in app.handlers.values():
        for h in group:
            if hasattr(h, "callback") and h.callback.__name__ == name:
                return h
    return None


@pytest.mark.asyncio
async def test_fluxo_completo_hardware_simples(monkeypatch):
    """
    Fluxo completo:
    start -> tipo (redireciona para descricao) -> problema simples
    NÃO abre ticket
    """

    app = run_bot(token="fake-token")

    start_handler = get_handler(app, "start")
    msg_handler = get_handler(app, "handle_message")

    context = SimpleNamespace(user_data={})

    # START
    update = FakeUpdate()
    await start_handler.callback(update, context)

    assert context.user_data["step"] == "tipo"

    # TIPO (redireciona direto para descricao)
    update = FakeUpdate("qualquer coisa")
    await msg_handler.callback(update, context)

    assert context.user_data["step"] == "descricao"

    # DESCRIÇÃO SIMPLES
    called = {"ticket": False}

    async def fake_ticket(update, user, ctx):
        called["ticket"] = True

    monkeypatch.setattr("app.bot.bot.criar_ticket", fake_ticket)

    update = FakeUpdate("internet lenta")
    await msg_handler.callback(update, context)

    assert context.user_data["step"] == "aguardando_confirmacao"
    assert called["ticket"] is False


@pytest.mark.asyncio
async def test_fluxo_completo_software_ticket(monkeypatch):
    """
    Fluxo completo: tipo → descricao → oferece solução → usuário escolhe abrir chamado
    """

    app = run_bot(token="fake-token")

    start_handler = get_handler(app, "start")
    msg_handler = get_handler(app, "handle_message")

    context = SimpleNamespace(user_data={})

    # START
    update = FakeUpdate()
    await start_handler.callback(update, context)

    # TIPO (redireciona direto para descricao)
    update = FakeUpdate("qualquer coisa")
    await msg_handler.callback(update, context)

    assert context.user_data["step"] == "descricao"

    # DESCRIÇÃO COMPLEXA
    called = {"ticket": False}

    async def fake_ticket(update, user, ctx):
        called["ticket"] = True

    monkeypatch.setattr("app.bot.bot.criar_ticket", fake_ticket)

    update = FakeUpdate("erro crítico no sistema financeiro")
    await msg_handler.callback(update, context)

    # Agora está em aguardando_confirmacao, oferecendo opções
    assert context.user_data["step"] == "aguardando_confirmacao"
    assert called["ticket"] is False  # Ainda não criou

    # Usuário escolhe ABRIR CHAMADO
    update = FakeUpdate("❌ Abrir chamado agora")
    await msg_handler.callback(update, context)

    # Agora sim cria ticket
    assert called["ticket"] is True
    assert context.user_data["step"] == "finalizado"


@pytest.mark.asyncio
async def test_run_bot_handlers_registrados():
    """
    Garante que o run_bot registra handlers corretamente
    """

    app = run_bot(token="fake-token")

    handlers = []
    for group in app.handlers.values():
        for h in group:
            handlers.append(h.callback.__name__)

    assert "start" in handlers
    assert "handle_message" in handlers