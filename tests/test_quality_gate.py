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


def test_close_ticket_sucesso(client):
    """Testa fechamento bem-sucedido de ticket"""
    with patch("app.api.app.SessionLocal") as mock_session, \
         patch("app.api.app.utcnow") as mock_utcnow, \
         patch("app.api.app.ADMIN_IDS", ["admin"]):

        # Mock do banco
        mock_db = Mock()
        mock_ticket = Mock()
        mock_ticket.id = 1
        mock_ticket.status = "aberto"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_ticket
        mock_session.return_value = mock_db

        # Mock do datetime
        mock_utcnow.return_value = "2024-01-01T00:00:00"

        # Fazer requisição
        resp = client.post("/ticket/1/close", json={"admin": "admin", "notes": "Resolvido"})

        # Verificações
        assert resp.status_code == 200
        assert resp.json["status"] == "fechado"

        # Verificar se os campos foram atualizados
        assert mock_ticket.status == "fechado"
        assert mock_ticket.closed_at == "2024-01-01T00:00:00"
        assert mock_ticket.closed_by == "admin"
        assert mock_ticket.admin_notes == "Resolvido"
        mock_db.commit.assert_called_once()


def test_close_ticket_erro_interno(client):
    """Testa tratamento de erro interno na rota close_ticket"""
    with patch("app.api.app.SessionLocal") as mock_session, \
         patch("app.api.app.ADMIN_IDS", ["admin"]):
        # Mock que lança exceção
        mock_db = Mock()
        mock_db.query.side_effect = Exception("erro de banco")
        mock_session.return_value = mock_db

        resp = client.post("/ticket/1/close", json={"admin": "admin"})

        assert resp.status_code == 500
        assert "error" in resp.json
        mock_db.rollback.assert_called_once()


def test_close_ticket_not_found_detalhado(client):
    """Testa quando ticket não é encontrado"""
    with patch("app.api.app.SessionLocal") as mock_session, \
         patch("app.api.app.ADMIN_IDS", ["admin"]):
        # Mock que retorna None
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_db

        resp = client.post("/ticket/999/close", json={"admin": "admin"})

        assert resp.status_code == 404
        assert resp.json["error"] == "not found"
