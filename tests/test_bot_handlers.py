import pytest
from types import SimpleNamespace
from app.bot.bot import run_bot


class FakeMessage:
    def __init__(self, text=""):
        self.texts = []
        self.text = text

    async def reply_text(self, text, reply_markup=None):
        self.texts.append(text)


class FakeUpdate:
    def __init__(self, text=""):
        self.message = FakeMessage(text)


@pytest.mark.asyncio
async def test_handle_message_fluxo_simples(monkeypatch):
    """
    Fluxo:
    tipo (redireciona) -> descrição simples
    NÃO deve abrir ticket
    """

    app = run_bot(token="fake-token")

    # pega o handler de mensagem corretamente
    message_handler = None
    for group in app.handlers.values():
        for h in group:
            if hasattr(h, "callback") and h.callback.__name__ == "handle_message":
                message_handler = h

    assert message_handler is not None

    context = SimpleNamespace(user_data={"step": "tipo"})

    # =========================
    # STEP 1 - tipo (redireciona para descricao)
    # =========================
    update = FakeUpdate("qualquer texto")
    await message_handler.callback(update, context)

    assert context.user_data["step"] == "descricao"
    assert len(update.message.texts) == 1

    # =========================
    # STEP 2 - descrição simples
    # =========================
    update = FakeUpdate("internet lenta")

    # mock criar_ticket (não deve ser chamado)
    called = {"ticket": False}

    async def fake_ticket(update, user, ctx):
        called["ticket"] = True

    monkeypatch.setattr("app.bot.bot.criar_ticket", fake_ticket)

    await message_handler.callback(update, context)

    # valida comportamento
    assert context.user_data["step"] == "aguardando_confirmacao"
    assert called["ticket"] is False
    assert len(update.message.texts) >= 1


@pytest.mark.asyncio
async def test_handle_message_abre_ticket(monkeypatch):
    """
    Fluxo com problema complexo:
    descricao → aguardando_confirmacao → usuário escolhe abrir chamado → cria ticket
    """

    app = run_bot(token="fake-token")

    message_handler = None
    for group in app.handlers.values():
        for h in group:
            if hasattr(h, "callback") and h.callback.__name__ == "handle_message":
                message_handler = h

    context = SimpleNamespace(user_data={
        "step": "descricao"
    })

    update = FakeUpdate("servidor caiu e não sobe")

    called = {"ticket": False}

    async def fake_ticket(update, user, ctx):
        called["ticket"] = True

    monkeypatch.setattr("app.bot.bot.criar_ticket", fake_ticket)

    # Primeira mensagem com descrição
    await message_handler.callback(update, context)

    # Vai para aguardando_confirmacao, NÃO cria ticket ainda
    assert context.user_data["step"] == "aguardando_confirmacao"
    assert called["ticket"] is False

    # Usuário escolhe abrir chamado
    update = FakeUpdate("❌ Abrir chamado agora")
    await message_handler.callback(update, context)

    # Agora cria ticket
    assert called["ticket"] is True
    assert context.user_data["step"] == "finalizado"
    assert context.user_data["step"] == "finalizado"


@pytest.mark.asyncio
async def test_handle_message_confirmacao(monkeypatch):
    """
    Step tentando_solucao:
    Usuário diz que NÃO resolveu → deve abrir ticket
    """

    app = run_bot(token="fake-token")

    message_handler = None
    for group in app.handlers.values():
        for h in group:
            if hasattr(h, "callback") and h.callback.__name__ == "handle_message":
                message_handler = h

    context = SimpleNamespace(user_data={
        "step": "tentando_solucao",
        "descricao": "internet lenta"
    })

    update = FakeUpdate("❌ Ainda não funcionou")

    called = {"ticket": False}

    async def fake_ticket(update, user, ctx):
        called["ticket"] = True

    monkeypatch.setattr("app.bot.bot.criar_ticket", fake_ticket)

    await message_handler.callback(update, context)

    assert called["ticket"] is True
    assert context.user_data["step"] == "finalizado"
    assert context.user_data["step"] == "finalizado"