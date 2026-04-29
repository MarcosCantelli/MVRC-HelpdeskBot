from app.api.app import app


def test_create_ticket_full():
    client = app.test_client()

    response = client.post("/ticket", json={
        "user": "teste",
        "category": "hardware",
        "subcategory": "impressora",
        "description": "teste",
        "ai_suggestion": "reiniciar"
    })

    assert response.status_code == 201
    data = response.get_json()

    assert "id" in data
    assert data["status"] == "aberto"