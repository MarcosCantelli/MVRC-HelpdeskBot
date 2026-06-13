import os
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

        # Mock de env pois a checagem agora recarrega os admin IDs dinamicamente
        with patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "12345"}, clear=False):
            result = is_admin(mock_update)
            assert result is True

    def test_is_admin_falso(self):
        """Testa is_admin quando usuário não é admin"""
        mock_user = Mock()
        mock_user.id = 99999

        mock_update = Mock()
        mock_update.effective_user = mock_user

        with patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "12345"}, clear=False):
            result = is_admin(mock_update)
            assert result is False

    def test_is_admin_sem_user_id(self):
        """Testa is_admin quando get_user_id retorna vazio"""
        mock_update = Mock()
        mock_update.effective_user = None

        with patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "12345"}, clear=False):
            result = is_admin(mock_update)
            assert result is False

    def test_is_admin_com_telegram_admin_id_env(self):
        """Testa is_admin com TELEGRAM_ADMIN_ID presente"""
        mock_user = Mock()
        mock_user.id = 12345

        mock_update = Mock()
        mock_update.effective_user = mock_user

        with patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": "12345"}, clear=False):
            result = is_admin(mock_update)
            assert result is True

    def test_is_admin_com_telegram_admin_id_hifen_env(self):
        """Testa is_admin com telegram-admin-id presente"""
        mock_user = Mock()
        mock_user.id = 67890

        mock_update = Mock()
        mock_update.effective_user = mock_user

        with patch.dict(os.environ, {"telegram-admin-id": "67890"}, clear=False):
            result = is_admin(mock_update)
            assert result is True

    def test_is_admin_com_TELEGRAM_ADMIN_ID_hifen_uppercase_env(self):
        """Testa is_admin com TELEGRAM-ADMIN-ID presente"""
        mock_user = Mock()
        mock_user.id = 22222

        mock_update = Mock()
        mock_update.effective_user = mock_user

        with patch.dict(os.environ, {"TELEGRAM-ADMIN-ID": "22222"}, clear=False):
            result = is_admin(mock_update)
            assert result is True

    def test_is_admin_com_telegram_admin_id_underscore_env(self):
        """Testa is_admin com telegram_admin_id presente"""
        mock_user = Mock()
        mock_user.id = 11111

        mock_update = Mock()
        mock_update.effective_user = mock_user

        with patch.dict(os.environ, {"telegram_admin_id": "11111"}, clear=False):
            result = is_admin(mock_update)
            assert result is True

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