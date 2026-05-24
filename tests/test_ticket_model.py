from app.models.ticket import Ticket


def test_ticket_model():
    ticket = Ticket(
        user="teste",
        description="problema teste"
    )

    assert ticket.user == "teste"
    assert ticket.description == "problema teste"