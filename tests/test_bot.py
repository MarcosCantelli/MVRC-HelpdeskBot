import pytest
from unittest.mock import AsyncMock, patch
from app.bot.bot import responder_automatico, criar_payload, criar_ticket


# =========================
# TESTES BOT
# =========================

def test_internet_lenta():
    resp = responder_automatico("internet lenta")
    assert "reiniciar" in resp.lower()


def test_sem_conexao():
    resp = responder_automatico("sem conexão")
    assert resp is not None


def test_texto_desconhecido():
    resp = responder_automatico("qualquer coisa")
    assert "suporte" in resp.lower()


def test_texto_vazio():
    resp = responder_automatico("")
    assert resp is not None


def test_texto_none():
    resp = responder_automatico(None)
    assert resp is not None

def test_faq_impressora():
    resp = responder_automatico("impressora não imprime")
    assert "impressora" in resp.lower()


def test_faq_computador():
    resp = responder_automatico("computador não liga")
    assert "energia" in resp.lower()


def test_faq_filamento():
    resp = responder_automatico("problema com filamento")
    assert "filamento" in resp.lower()
    
def test_internet_generico():
    resp = responder_automatico("internet caiu geral")
    assert resp is not None

def test_enviar_ticket_mock():
    def fake_post(url, json):
        return type("Resp", (), {"json": lambda: {"id": 123}})()

    payload = {"user": "teste"}

    resp = enviar_ticket(payload, request_func=fake_post)

    assert resp["id"] == 123

# =========================
# TESTES PAYLOAD
# =========================

def test_criar_payload():
    context = {
        "descricao": "teste",
        "category": "hardware",
        "subcategory": "pc",
        "ai": "reiniciar"
    }

    payload = criar_payload("user1", context)

    assert payload["user"] == "user1"
    assert payload["description"] == "teste"
    assert payload["category"] == "hardware"


# =========================
# TESTES CRIAR TICKET
# =========================

@pytest.mark.asyncio
@patch("app.bot.bot.requests.post")
async def test_criar_ticket_sucesso(mock_post):
    mock_post.return_value.json.return_value = {"id": 123}

    update = AsyncMock()
    update.message.reply_text = AsyncMock()

    context = {"descricao": "teste"}

    await criar_ticket(update, "user1", context)

    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch("app.bot.bot.requests.post", side_effect=Exception("erro"))
async def test_criar_ticket_erro(mock_post):
    update = AsyncMock()
    update.message.reply_text = AsyncMock()

    context = {"descricao": "teste"}

    await criar_ticket(update, "user1", context)

    update.message.reply_text.assert_called_once()