import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# 🔥 Detecta se está rodando em ambiente de teste
TEST_ENV = os.getenv("TEST_ENV") == "true"

if TEST_ENV:
    # 🧪 Banco leve para testes (não precisa de Postgres)
    DATABASE_URL = "sqlite:///./test.db"
else:
    # 🌍 Produção / desenvolvimento
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    # 🔒 Validação básica (evita erro silencioso)
    if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
        raise ValueError("❌ Variáveis de ambiente do banco não configuradas corretamente")

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 🔧 Config extra para SQLite (necessário)
connect_args = {"check_same_thread": False} if TEST_ENV else {}

engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()