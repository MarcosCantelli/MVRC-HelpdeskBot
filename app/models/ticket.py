from sqlalchemy import Column, Integer, String
from app.database.db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String)
    category = Column(String)       # hardware / software
    subcategory = Column(String)    # impressora / 3d
    description = Column(String)
    ai_suggestion = Column(String)
    status = Column(String, default="aberto")