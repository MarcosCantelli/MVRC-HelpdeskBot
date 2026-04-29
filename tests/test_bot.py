from app.bot.bot import responder_automatico


def test_resposta_internet_lenta():
    resposta = responder_automatico("internet lenta")
    assert "reiniciar" in resposta.lower()


def test_resposta_sem_conexao():
    resposta = responder_automatico("sem conexão")
    assert resposta is not None
    assert isinstance(resposta, str)


def test_resposta_desconhecida():
    resposta = responder_automatico("problema totalmente aleatório")
    assert resposta is not None
    assert "suporte" in resposta.lower() or "não entendi" in resposta.lower()


def test_resposta_vazia():
    resposta = responder_automatico("")
    assert resposta is not None


def test_resposta_none():
    resposta = responder_automatico(None)
    assert resposta is not None