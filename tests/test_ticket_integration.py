from app.bot.bot import enviar_ticket


def test_enviar_ticket_sucesso():
    def fake_post(url, json):
        class Response:
            def json(self):
                return {"id": 123}
        return Response()

    result = enviar_ticket({"teste": "ok"}, request_func=fake_post)

    assert result["id"] == 123


def test_enviar_ticket_erro():
    def fake_post(url, json):
        raise Exception("erro")

    result = enviar_ticket({"teste": "ok"}, request_func=fake_post)

    assert result is None