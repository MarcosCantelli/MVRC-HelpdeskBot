from app.database.db import SessionLocal
from app.models.ticket import Ticket


def test_db_insert():
    db = SessionLocal()

    ticket = Ticket(user="teste", description="teste")
    db.add(ticket)
    db.commit()

    assert ticket.id is not None

    db.close()