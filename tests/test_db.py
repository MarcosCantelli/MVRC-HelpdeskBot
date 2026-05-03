from app.database.db import SessionLocal
from app.models.ticket import Ticket
import pytest
import os
from unittest.mock import patch


def test_db_insert():
    db = SessionLocal()

    ticket = Ticket(user="teste", description="teste")
    db.add(ticket)
    db.commit()

    assert ticket.id is not None

    db.close()


def test_database_url_configurada():
    """Testa que DATABASE_URL é configurada corretamente"""
    # Quando TEST_ENV=true, deve usar sqlite:///:memory:
    with patch.dict(os.environ, {"TEST_ENV": "true"}):
        # Reimportar o módulo para recarregar as configurações
        import importlib
        import app.database.db
        importlib.reload(app.database.db)

        # Verificar que DATABASE_URL foi configurada
        assert app.database.db.DATABASE_URL == "sqlite:///:memory:"
        assert "sqlite" in app.database.db.DATABASE_URL


def test_database_url_nao_configurada():
    """Testa que ValueError é lançada quando DATABASE_URL não está configurada"""
    with patch.dict(os.environ, {"TEST_ENV": "false", "DATABASE_URL": ""}, clear=True):
        with pytest.raises(ValueError, match="DATABASE_URL não configurada"):
            # Reimportar o módulo para recarregar as configurações
            import importlib
            import app.database.db
            importlib.reload(app.database.db)


def test_engine_config_postgres():
    """Testa configuração do engine para PostgreSQL"""
    postgres_url = "postgresql://user:pass@localhost:5432/db"

    with patch.dict(os.environ, {"TEST_ENV": "false", "DATABASE_URL": postgres_url}):
        import importlib
        import app.database.db
        importlib.reload(app.database.db)

        # Verificar configurações do pool para PostgreSQL
        engine_kwargs = app.database.db.engine_kwargs
        assert engine_kwargs["pool_pre_ping"] is True
        assert engine_kwargs["pool_size"] == 5
        assert engine_kwargs["max_overflow"] == 10


def test_engine_config_sqlite():
    """Testa configuração do engine para SQLite"""
    with patch.dict(os.environ, {"TEST_ENV": "true"}):
        import importlib
        import app.database.db
        importlib.reload(app.database.db)

        # Verificar configurações para SQLite
        engine_kwargs = app.database.db.engine_kwargs
        assert engine_kwargs["connect_args"] == {"check_same_thread": False}