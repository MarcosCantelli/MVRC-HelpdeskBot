from app.bot.bot import notificar_telegram


class MockResponse:
    pass


def mock_post_ok(url, json):
    return MockResponse()


def mock_post_fail(url, json):
    raise Exception("erro")


def test_notificar_telegram_sucesso(monkeypatch):
    monkeypatch.setattr("app.bot.bot.TELEGRAM_CHAT_ID", "123")

    resp = notificar_telegram("user", 1, request_func=mock_post_ok)
    assert resp is not None


def test_notificar_telegram_erro(monkeypatch):
    monkeypatch.setattr("app.bot.bot.TELEGRAM_CHAT_ID", "123")

    resp = notificar_telegram("user", 1, request_func=mock_post_fail)
    assert resp is None


def test_notificar_sem_chat_id(monkeypatch):
    monkeypatch.setattr("app.bot.bot.TELEGRAM_CHAT_ID", None)

    resp = notificar_telegram("user", 1)
    assert resp is None