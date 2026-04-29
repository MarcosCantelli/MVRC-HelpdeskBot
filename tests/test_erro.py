from app.api.app import create_ticket_service


def test_payload_invalido():
    response, status = create_ticket_service(None)
    assert status == 400