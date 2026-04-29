from sqlalchemy import Column, Integer, String
from app.database.db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, nullable=False)
    category = Column(String)
    subcategory = Column(String)
    description = Column(String, nullable=False)
    ai_suggestion = Column(String)
    status = Column(String, default="aberto")