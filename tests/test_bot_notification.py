from app.bot.bot import notificar_telegram


class MockResponse:
    status_code = 200

    def json(self):
        return {"ok": True}


def mock_post_ok(url, json):
    return MockResponse()


def mock_post_fail(url, json):
    raise Exception("erro")


def test_notificar_telegram_sucesso(monkeypatch):
    monkeypatch.setattr("app.bot.bot.TELEGRAM_CHAT_ID", "123")
    # A função agora também valida se o TOKEN está configurado antes
    # de tentar notificar, retornando None (e logando) caso não esteja.
    # Em ambiente de teste TOKEN normalmente é vazio, então precisamos
    # garantir que está presente para o cenário de sucesso.
    monkeypatch.setattr("app.bot.bot.TOKEN", "fake-token")

    resp = notificar_telegram("user", 1, request_func=mock_post_ok)
    assert resp is not None


def test_notificar_telegram_erro(monkeypatch):
    monkeypatch.setattr("app.bot.bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("app.bot.bot.TOKEN", "fake-token")

    resp = notificar_telegram("user", 1, request_func=mock_post_fail)
    assert resp is None


def test_notificar_sem_chat_id(monkeypatch):
    monkeypatch.setattr("app.bot.bot.TELEGRAM_CHAT_ID", None)
    monkeypatch.setattr("app.bot.bot.TOKEN", "fake-token")

    resp = notificar_telegram("user", 1)
    assert resp is None


def test_notificar_sem_token(monkeypatch):
    """
    Quando TELEGRAM_TOKEN não está configurado, a notificação não deve
    ser enviada (a função registra isso via log e retorna None),
    mesmo havendo um TELEGRAM_CHAT_ID válido.
    """
    monkeypatch.setattr("app.bot.bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("app.bot.bot.TOKEN", None)

    resp = notificar_telegram("user", 1, request_func=mock_post_ok)
    assert resp is None