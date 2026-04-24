from sqlalchemy import Column, Integer, String
from app.database.db import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String)
    description = Column(String)
    status = Column(String, default="aberto")