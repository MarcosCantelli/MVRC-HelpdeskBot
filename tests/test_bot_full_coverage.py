import pytest
from types import SimpleNamespace

from app.bot.bot import (
    criar_ticket,
    enviar_ticket,
    sugerir_solucao
)

# =========================
# MOCK TELEGRAM
# =========================
class FakeMessage:
    def __init__(self):
        self.texts = []

    async def reply_text(self, text):
        self.texts.append(text)


class FakeUpdate:
    def __init__(self):
        self.message = FakeMessage()


# =========================
# MOCK REQUESTS
# =========================
class MockResponseOK:
    def json(self):
        return {"id": 999}


class MockResponseNoJson:
    pass


def mock_post_success(url, json):
    return MockResponseOK()


def mock_post_nojson(url, json):
    return MockResponseNoJson()


def mock_post_error(url, json):
    raise Exception("erro")


# =========================
# TESTES criar_ticket
# =========================
@pytest.mark.asyncio
async def test_criar_ticket_sucesso(monkeypatch):
    update = FakeUpdate()
    context = {"descricao": "teste"}

    monkeypatch.setattr(
        "app.bot.bot.enviar_ticket",
        lambda payload: {"id": 1}
    )

    await criar_ticket(update, "user", context)

    assert any("Chamado" in msg for msg in update.message.texts)


@pytest.mark.asyncio
async def test_criar_ticket_erro(monkeypatch):
    update = FakeUpdate()
    context = {"descricao": "teste"}

    monkeypatch.setattr(
        "app.bot.bot.enviar_ticket",
        lambda payload: None
    )

    await criar_ticket(update, "user", context)

    assert any("Erro" in msg for msg in update.message.texts)


@pytest.mark.asyncio
async def test_criar_ticket_exception(monkeypatch):
    update = FakeUpdate()
    context = {"descricao": "teste"}

    def explode(payload):
        raise Exception("fail")

    monkeypatch.setattr("app.bot.bot.enviar_ticket", explode)

    await criar_ticket(update, "user", context)

    assert any("Erro" in msg for msg in update.message.texts)


# =========================
# TESTES enviar_ticket EXTRA
# =========================
def test_enviar_ticket_sem_json():
    resp = enviar_ticket({}, request_func=mock_post_nojson)
    assert resp is None


def test_enviar_ticket_exception():
    resp = enviar_ticket({}, request_func=mock_post_error)
    assert resp is None


# =========================
# TESTES sugerir_solucao COMPLETOS
# =========================
def test_sugestao_lento():
    resp = sugerir_solucao("muito lento")
    assert "reiniciar" in resp.lower()


def test_sugestao_internet():
    resp = sugerir_solucao("internet caiu")
    assert "roteador" in resp.lower()


def test_sugestao_none():
    resp = sugerir_solucao(None)
    assert resp is not None