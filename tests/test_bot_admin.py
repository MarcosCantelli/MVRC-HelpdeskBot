from app.bot.bot import (
    mensagem_padrao,
    responder_automatico,
    problema_simples,
)


def test_mensagem_padrao():
    assert mensagem_padrao() is not None


def test_responder_none():
    resp = responder_automatico(None)

    assert "não entendi" in resp.lower()


def test_responder_conexao():
    resp = responder_automatico("sem conexão")

    assert "internet" in resp.lower()


def test_problema_simples_false():
    assert problema_simples("kernel panic") is False


def test_problema_simples_true():
    assert problema_simples("internet lenta") is True