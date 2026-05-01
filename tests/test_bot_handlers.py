import pytest
from types import SimpleNamespace
from app.bot.bot import run_bot


class FakeMessage:
    def __init__(self):
        self.texts = []
        self.text = "internet lenta"

    async def reply_text(self, text, reply_markup=None):
        self.texts.append(text)


class FakeUpdate:
    def __init__(self):
        self.message = FakeMessage()


@pytest.mark.asyncio
async def test_handle_message(monkeypatch):
    app = run_bot(token="fake-token")

    update = FakeUpdate()
    context = SimpleNamespace(user_data={})

    # pega handler manualmente
    handler = app.handlers[0][1]  # MessageHandler

    # mock criar_ticket
    async def fake_ticket(update, user, context):
        return None

    monkeypatch.setattr("app.bot.bot.TOKEN", "fake-token")

    await handler.callback(update, context)

    assert len(update.message.texts) >= 2