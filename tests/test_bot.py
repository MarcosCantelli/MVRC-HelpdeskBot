from app.bot.bot import responder_automatico


def test_internet_lenta():
    resp = responder_automatico("internet lenta")
    assert "reiniciar" in resp.lower()


def test_sem_conexao():
    resp = responder_automatico("sem conexão")
    assert resp is not None


def test_texto_desconhecido():
    resp = responder_automatico("qualquer coisa")
    assert "suporte" in resp.lower() or "não entendi" in resp.lower()


def test_texto_vazio():
    resp = responder_automatico("")
    assert resp is not None


def test_texto_none():
    resp = responder_automatico(None)
    assert resp is not None