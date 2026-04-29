from flask import Flask, request, jsonify
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

Base.metadata.create_all(bind=engine)

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


def create_ticket_service(data: dict):
    if not data:
        return {"error": "Payload vazio"}, 400

    if not data.get("user") or not data.get("description"):
        return {"error": "Campos obrigatórios: user, description"}, 400

    db = SessionLocal()

    try:
        ticket = Ticket(
            user=data["user"],
            category=data.get("category"),
            subcategory=data.get("subcategory"),
            description=data["description"],
            ai_suggestion=data.get("ai_suggestion")
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return {
            "id": ticket.id,
            "status": ticket.status
        }, 201

    except SQLAlchemyError:
        db.rollback()
        return {"error": "Erro no banco"}, 500

    finally:
        db.close()


@app.route("/ticket", methods=["POST"])
def create_ticket():
    if not request.is_json:
        return jsonify({"error": "JSON inválido"}), 400

    data = request.get_json()
    response, status = create_ticket_service(data)
    return jsonify(response), status