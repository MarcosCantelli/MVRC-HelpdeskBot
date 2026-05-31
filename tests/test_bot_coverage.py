import pytest
from app.bot.bot import enviar_ticket, sugerir_solucao


# =========================
# MOCK REQUEST
# =========================
class MockResponse:
    def json(self):
        return {"id": 123}


def mock_post_success(url, json):
    return MockResponse()


def mock_post_fail(url, json):
    raise Exception("erro")


# =========================
# TESTES enviar_ticket
# =========================
def test_enviar_ticket_sucesso():
    payload = {"test": "ok"}
    resp = enviar_ticket(payload, request_func=mock_post_success)
    assert resp["id"] == 123


def test_enviar_ticket_erro():
    payload = {"test": "ok"}
    resp = enviar_ticket(payload, request_func=mock_post_fail)
    assert resp is None


# =========================
# TESTES sugerir_solucao
# =========================
def test_sugestao_internet():
    resp = sugerir_solucao("internet caiu")
    assert "roteador" in resp.lower()


def test_sugestao_padrao():
    resp = sugerir_solucao("abcxyz")
    assert resp is not None


# =========================
# TESTES responder_automatico
# =========================
def test_resposta_sem_conexao():
    resp = responder_automatico("sem conexão")
    assert "verificar conexão" in resp.lower()


def test_resposta_none():
    resp = responder_automatico(None)
    assert "suporte" in resp.lower()