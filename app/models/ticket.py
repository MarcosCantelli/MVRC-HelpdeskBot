from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.database.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_code = Column(String, unique=True, index=True)

    user = Column(String, nullable=False)

    category = Column(String)
    subcategory = Column(String)

    description = Column(String, nullable=False)
    ai_suggestion = Column(String)

    status = Column(String, default="aberto", nullable=False)

    # 🔥 NOVO
    created_at = Column(DateTime(timezone=True), default=utcnow)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # 🔥 ADMIN
    closed_by = Column(String, nullable=True)
    admin_notes = Column(String, nullable=True)