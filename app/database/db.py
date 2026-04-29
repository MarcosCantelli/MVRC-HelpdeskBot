import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

TEST_ENV = os.getenv("TEST_ENV") == "true"

if TEST_ENV:
    DATABASE_URL = "sqlite:///./test.db"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()