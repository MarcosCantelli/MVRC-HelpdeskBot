import pytest
from app.api.app import app
from unittest.mock import Mock, patch


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


def test_erro_interno_em_list_tickets(client):
    """Test que a rota /tickets trata erro interno com graceful handling"""
    with patch("app.api.app.SessionLocal") as mock_session:
        # Mock the query method to raise an exception
        mock_db = Mock()
        mock_db.query.side_effect = Exception("erro simulado")
        mock_session.return_value = mock_db
        
        resp = client.get("/tickets")
        # Deve retornar 500 em caso de erro
        assert resp.status_code == 500
        assert "error" in resp.json
