from app.api.app import app

def test_health():
    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert response.json["status"] == "ok"
    
def test_create_ticket():
    client = app.test_client()

    response = client.post("/ticket", json={
        "user": "teste",
        "description": "teste pipeline"
    })

    assert response.status_code == 200
    assert "id" in response.json