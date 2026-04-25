from flask import Flask, request, jsonify
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
import os

load_dotenv()

# 🔥 Cria tabela automaticamente se não existir
Base.metadata.create_all(bind=engine)

app = Flask(__name__)


@app.route("/ticket", methods=["POST"])
def create_ticket():
    data = request.json
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

        return jsonify({
            "id": ticket.id,
            "status": ticket.status
        })

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()