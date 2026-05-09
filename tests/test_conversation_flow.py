import pytest
from types import SimpleNamespace
from app.bot.bot import run_bot


class FakeUser:
    def __init__(self):
        self.id = 123
        self.full_name = "Teste User"
        self.username = "teste"


class FakeMessage:
    def __init__(self):
        self.texts = []
        self.text = ""

    async def reply_text(self, text, reply_markup=None):
        self.texts.append(text)


class FakeUpdate:
    def __init__(self):
        self.message = FakeMessage()
        self.effective_user = FakeUser()  # 🔥 ESSENCIAL


@pytest.mark.asyncio
async def test_fluxo_hardware_completo(monkeypatch):
    app = run_bot(token="fake-token")

    # 🔥 Encontra o MessageHandler (é o último na lista de handlers)
    message_handlers = [h for h in app.handlers[0] if h.__class__.__name__ == "MessageHandler"]
    handler = message_handlers[0]

    update = FakeUpdate()
    context = SimpleNamespace(user_data={})

    async def fake_ticket(update, user, context):
        update.message.texts.append("TICKET_CRIADO")

    monkeypatch.setattr("app.bot.bot.criar_ticket", fake_ticket)

    # 1️⃣ hardware
    update.message.text = "🖥️ Hardware"
    await handler.callback(update, context)

    assert "qual equipamento" in update.message.texts[-1].lower()

    # 2️⃣ equipamento
    update.message.text = "Computador"
    await handler.callback(update, context)

    assert "descreva o problema" in update.message.texts[-1].lower()

    # 3️⃣ problema complexo → cria ticket
    update.message.text = "computador com erro crítico"
    await handler.callback(update, context)

    assert "TICKET_CRIADO" in update.message.texts


@pytest.mark.asyncio
async def test_fluxo_software_sem_ticket(monkeypatch):
    app = run_bot(token="fake-token")

    # 🔥 Encontra o MessageHandler
    message_handlers = [h for h in app.handlers[0] if h.__class__.__name__ == "MessageHandler"]
    handler = message_handlers[0]

    update = FakeUpdate()
    context = SimpleNamespace(user_data={})

    # 1️⃣ software
    update.message.text = "💻 Software"
    await handler.callback(update, context)

    assert "qual equipamento" in update.message.texts[-1].lower()

    # 2️⃣ equipamento
    update.message.text = "Computador"
    await handler.callback(update, context)

    assert "descreva o problema" in update.message.texts[-1].lower()

    # 3️⃣ problema simples → NÃO cria ticket
    update.message.text = "internet lenta"
    await handler.callback(update, context)

    assert not any("Chamado" in t for t in update.message.texts)