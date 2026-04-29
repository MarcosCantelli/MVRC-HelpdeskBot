from app.bot.bot import responder_automatico


def test_resposta_automatica():
    resposta = responder_automatico("internet lenta")
    assert resposta is not None