import pytest
from app.bot.bot import criar_payload


def test_criar_payload_completo():
    context = {
        "descricao": "teste",
        "category": "infra",
        "subcategory": "rede",
        "ai": "sugestão"
    }

    payload = criar_payload("user1", context)

    assert payload["user"] == "user1"
    assert payload["description"] == "teste"
    assert payload["category"] == "infra"
    assert payload["subcategory"] == "rede"
    assert payload["ai_suggestion"] == "sugestão"


def test_criar_payload_vazio():
    payload = criar_payload("user2", {})

    assert payload["user"] == "user2"
    assert payload["description"] is None