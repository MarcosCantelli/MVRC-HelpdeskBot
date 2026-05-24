from app.api.app import app


def test_health():
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200


def test_create_ticket_sem_user():
    client = app.test_client()

    response = client.post("/ticket", json={
        "description": "teste"
    })

    assert response.status_code == 400


def test_create_ticket_sem_description():
    client = app.test_client()

    response = client.post("/ticket", json={
        "user": "teste"
    })

    assert response.status_code == 400


def test_get_ticket_not_found():
    client = app.test_client()

    response = client.get("/ticket/INVALID")

    assert response.status_code == 404


def test_list_tickets():
    client = app.test_client()

    response = client.get("/tickets")

    assert response.status_code == 200


def test_close_ticket_unauthorized():
    client = app.test_client()

    response = client.post(
        "/ticket/1/close",
        json={"admin": "999"}
    )

    assert response.status_code == 403


def test_update_status_unauthorized():
    client = app.test_client()

    response = client.patch(
        "/ticket/1/status",
        json={
            "admin": "999",
            "status": "encerrado"
        }
    )

    assert response.status_code == 403


def test_add_note_unauthorized():
    client = app.test_client()

    response = client.post(
        "/ticket/1/note",
        json={
            "admin": "999",
            "note": "teste"
        }
    )

    assert response.status_code == 403