import pytest
from unittest.mock import patch
from app.bot.bot import sugerir_solucao, criar_payload, enviar_ticket


# =========================
# TESTES IA (SUGESTÕES)
# =========================

def test_sugestao_internet():
    resp = sugerir_solucao("internet lenta")
    assert "roteador" in resp.lower() or "modem" in resp.lower()


def test_sugestao_lento():
    resp = sugerir_solucao("computador lento")
    assert "reiniciar" in resp.lower()


def test_sugestao_generica():
    resp = sugerir_solucao("qualquer coisa aleatória")
    assert resp is not None


def test_sugestao_none():
    resp = sugerir_solucao(None)
    assert resp is not None


# =========================
# TESTES PAYLOAD
# =========================

def test_criar_payload():
    context = {
        "descricao": "teste",
        "categoria": "hardware",
        "dispositivo": "pc",
        "sugestao": "reiniciar"
    }

    payload = criar_payload("user1", context)

    assert payload["user"] == "user1"
    assert payload["description"] == "teste"
    assert payload["category"] == "hardware"
    assert payload["subcategory"] == "pc"


# =========================
# TESTES API
# =========================

def test_enviar_ticket_mock():
    def fake_post(url, json):
        return type("Resp", (), {
            "json": lambda self: {"id": 999}
        })()

    with patch("app.bot.bot.requests.post", fake_post):
        resp = enviar_ticket({"user": "teste"})

    assert resp["id"] == 999


def test_enviar_ticket_erro():
    def fake_post(url, json):
        raise Exception("erro")

    with patch("app.bot.bot.requests.post", fake_post):
        resp = enviar_ticket({"user": "teste"})

    assert resp is None