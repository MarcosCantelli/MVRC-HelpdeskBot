import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# ======================================================
# TEST ENV
# ======================================================

TEST_ENV = os.getenv("TEST_ENV", "false").lower() == "true"

# ======================================================
# DATABASE URL
# ======================================================

if TEST_ENV:
    DATABASE_URL = "sqlite:///:memory:"
else:
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./test.db"

# ======================================================
# ENGINE CONFIG
# ======================================================

engine_kwargs = {}

# SQLite
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {
        "connect_args": {
            "check_same_thread": False
        }
    }

# PostgreSQL / Supabase
else:
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10
    }

# ======================================================
# ENGINE
# ======================================================

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)

# ======================================================
# SESSION
# ======================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ======================================================
# BASE
# ======================================================

Base = declarative_base()