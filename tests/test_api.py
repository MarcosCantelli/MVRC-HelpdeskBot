from app.api.app import app

def test_create_ticket():
    client = app.test_client()

    response = client.post("/ticket", json={
        "user": "teste",
        "description": "teste de chamado"
    })

    assert response.status_code == 200