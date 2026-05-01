import pytest
from types import SimpleNamespace
from app.bot.bot import run_bot


class FakeMessage:
    def __init__(self):
        self.texts = []
        self.text = ""

    async def reply_text(self, text, reply_markup=None):
        self.texts.append(text)


class FakeUpdate:
    def __init__(self):
        self.message = FakeMessage()


@pytest.mark.asyncio
async def test_fluxo_hardware_completo(monkeypatch):
    app = run_bot(token="fake-token")

    # pega handler
    handler = app.handlers[0][1]

    update = FakeUpdate()
    context = SimpleNamespace(user_data={})

    # mock ticket
    async def fake_ticket(update, user, context):
        update.message.texts.append("TICKET_CRIADO")

    monkeypatch.setattr("app.bot.bot.criar_ticket", fake_ticket)

    # 1️⃣ usuário escolhe hardware
    update.message.text = "🖥️ Hardware"
    await handler.callback(update, context)

    assert "qual equipamento" in update.message.texts[-1].lower()

    # 2️⃣ escolhe dispositivo
    update.message.text = "Computador"
    await handler.callback(update, context)

    assert "descreva o problema" in update.message.texts[-1].lower()

    # 3️⃣ descreve problema crítico
    update.message.text = "computador com erro"
    await handler.callback(update, context)

    assert "TICKET_CRIADO" in update.message.texts


@pytest.mark.asyncio
async def test_fluxo_software_sem_ticket(monkeypatch):
    app = run_bot(token="fake-token")

    handler = app.handlers[0][1]

    update = FakeUpdate()
    context = SimpleNamespace(user_data={})

    update.message.text = "💻 Software"
    await handler.callback(update, context)

    assert "descreva o problema" in update.message.texts[-1].lower()

    update.message.text = "preciso instalar um programa"
    await handler.callback(update, context)

    # não deve abrir ticket
    assert not any("Chamado" in t for t in update.message.texts)