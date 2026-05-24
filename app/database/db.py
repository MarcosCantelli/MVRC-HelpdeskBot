import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

TEST_ENV = os.getenv("TEST_ENV", "false").lower() == "true"

# =========================
# DATABASE URL
# =========================

if TEST_ENV:
    DATABASE_URL = "sqlite:///:memory:"
else:
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada")

# =========================
# ENGINE CONFIG
# =========================

engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {
        "connect_args": {"check_same_thread": False}
    }
else:
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10
    }

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)