import pytest
from unittest.mock import Mock, patch, AsyncMock
from telegram import Update, User
from telegram.ext import ContextTypes
from app.bot.bot import (
    get_user, get_user_id, is_admin,
    listar_tickets, fechar_ticket, run_bot
)


class TestBotUtils:
    """Testes para funções utilitárias do bot"""

    @pytest.mark.asyncio
    async def test_aliases_de_comandos_admin(self):
        """Testa aliases em português para comandos administrativos."""
        app = run_bot(token="fake-token")

        commands = {
            name for handler in app.handlers[0]
            if hasattr(handler, "commands")
            for name in handler.commands
        }

        assert {"lista", "entrar", "encerrar", "fechar"}.issubset(commands)

    def test_get_user_com_user(self):
        """Testa get_user quando update tem effective_user"""
        mock_user = Mock()
        mock_user.full_name = "João Silva"
        mock_user.username = "joao"

        mock_update = Mock()
        mock_update.effective_user = mock_user

        result = get_user(mock_update)
        assert result == "João Silva"

    def test_get_user_sem_full_name(self):
        """Testa get_user quando não tem full_name"""
        mock_user = Mock()
        mock_user.full_name = None
        mock_user.username = "joao"

        mock_update = Mock()
        mock_update.effective_user = mock_user

        result = get_user(mock_update)
        assert result == "joao"

    def test_get_user_sem_user(self):
        """Testa get_user quando não tem effective_user"""
        mock_update = Mock()
        mock_update.effective_user = None

        result = get_user(mock_update)
        assert result == "anonimo"

    def test_get_user_id_com_user(self):
        """Testa get_user_id quando tem effective_user"""
        mock_user = Mock()
        mock_user.id = 12345

        mock_update = Mock()
        mock_update.effective_user = mock_user

        result = get_user_id(mock_update)
        assert result == "12345"

    def test_get_user_id_sem_user(self):
        """Testa get_user_id quando não tem effective_user"""
        mock_update = Mock()
        mock_update.effective_user = None

        result = get_user_id(mock_update)
        assert result == ""

    def test_is_admin_verdadeiro(self):
        """Testa is_admin quando usuário é admin"""
        mock_user = Mock()
        mock_user.id = 12345

        mock_update = Mock()
        mock_update.effective_user = mock_user

        # Mock das variáveis globais
        with patch("app.bot.bot.ADMIN_IDS", ["12345"]):
            result = is_admin(mock_update)
            assert result is True

    def test_is_admin_falso(self):
        """Testa is_admin quando usuário não é admin"""
        mock_user = Mock()
        mock_user.id = 99999

        mock_update = Mock()
        mock_update.effective_user = mock_user

        with patch("app.bot.bot.ADMIN_IDS", ["12345"]):
            result = is_admin(mock_update)
            assert result is False

    def test_is_admin_sem_user_id(self):
        """Testa is_admin quando get_user_id retorna vazio"""
        mock_update = Mock()
        mock_update.effective_user = None

        with patch("app.bot.bot.ADMIN_IDS", ["12345"]):
            result = is_admin(mock_update)
            assert result is False

    @patch("app.bot.bot.requests.get")
    def test_listar_tickets_sucesso(self, mock_get):
        """Testa listar_tickets com sucesso"""
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1, "code": "TK001"}]
        mock_get.return_value = mock_response

        result = listar_tickets()
        assert result == [{"id": 1, "code": "TK001"}]
        mock_get.assert_called_once()

    @patch("app.bot.bot.requests.get")
    def test_listar_tickets_erro(self, mock_get):
        """Testa listar_tickets com erro"""
        mock_get.side_effect = Exception("erro de rede")

        result = listar_tickets()
        assert result == []

    @patch("app.bot.bot.requests.post")
    def test_fechar_ticket_sucesso(self, mock_post):
        """Testa fechar_ticket com sucesso"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "fechado"}
        mock_post.return_value = mock_response

        result = fechar_ticket("1", "admin")
        assert result == {"status": "fechado"}

    @patch("app.bot.bot.requests.post")
    def test_fechar_ticket_erro(self, mock_post):
        """Testa fechar_ticket com erro"""
        mock_post.side_effect = Exception("erro de rede")

        result = fechar_ticket("1", "admin")
        assert result is None