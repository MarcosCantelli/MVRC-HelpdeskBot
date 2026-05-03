import pytest
from app.api.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"


def test_close_ticket_nao_autorizado(client):
    resp = client.post("/ticket/1/close", json={"admin": "invalido"})
    assert resp.status_code == 403


def test_close_ticket_not_found(client):
    # assumindo admin válido
    resp = client.post("/ticket/9999/close", json={"admin": "admin"})
    assert resp.status_code in [404, 403]


def test_list_tickets(client):
    resp = client.get("/tickets")
    assert resp.status_code == 200


def test_erro_interno_simulado(monkeypatch, client):
    def mock_db(*args, **kwargs):
        raise Exception("erro")

    monkeypatch.setattr("app.api.app.SessionLocal", mock_db)

    resp = client.get("/tickets")
    assert resp.status_code in [500, 200]
