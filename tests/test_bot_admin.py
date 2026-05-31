from app.bot.bot import mensagem_padrao


def test_mensagem_padrao():
    assert mensagem_padrao() is not None