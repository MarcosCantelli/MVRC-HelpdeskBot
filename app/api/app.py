from flask import Flask, request, jsonify
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
import os
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import func

logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

# ==============================
# INIT DB
# ==============================
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.exception("Erro ao inicializar banco de dados")


# ==============================
# GERAR CÓDIGO
# ==============================
def gerar_ticket_code(db, category):
    ano = datetime.now().year
    prefixo = "HW" if category == "hardware" else "SW"

    total = db.query(func.count(Ticket.id)).scalar() or 0
    numero = str(total + 1).zfill(3)

    return f"TK{prefixo}{ano}{numero}"


# ==============================
# CREATE
# ==============================
def create_ticket_service(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    if not data or not data.get("user") or not data.get("description"):
        return {"error": "Campos obrigatórios"}, 400

    db = SessionLocal()

    try:
        ticket_code = gerar_ticket_code(db, data.get("category"))

        ticket = Ticket(
            ticket_code=ticket_code,
            user=data["user"],
            category=data.get("category"),
            subcategory=data.get("subcategory"),
            description=data["description"],
            ai_suggestion=data.get("ai_suggestion"),
            status="aberto"
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return {
            "id": ticket.id,
            "ticket_code": ticket.ticket_code,
            "status": ticket.status,
            "created_at": ticket.created_at
        }, 201

    except Exception as e:
        db.rollback()
        logger.exception("Erro ao criar ticket")
        return {"error": "erro interno"}, 500

    finally:
        db.close()


# ==============================
# LISTAR TICKETS
# ==============================
@app.route("/tickets", methods=["GET"])
def list_tickets():
    db = None

    try:
        db = SessionLocal()
        tickets = db.query(Ticket).all()

        return jsonify([
            {
                "id": t.id,
                "code": t.ticket_code,
                "user": t.user,
                "status": t.status,
                "created_at": t.created_at,
                "closed_at": t.closed_at
            } for t in tickets
        ]), 200

    except Exception as e:
        logger.exception("Erro ao listar tickets")
        return {"error": "erro interno"}, 500

    finally:
        if db:
            db.close()


# ==============================
# FECHAR TICKET
# ==============================
@app.route("/ticket/<int:ticket_id>/close", methods=["POST"])
def close_ticket(ticket_id):
    data = request.get_json() or {}
    admin_id = str(data.get("admin"))

    if admin_id not in ADMIN_IDS:
        return {"error": "não autorizado"}, 403

    db = SessionLocal()

    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

        if not ticket:
            return {"error": "not found"}, 404

        ticket.status = "fechado"
        ticket.closed_at = datetime.utcnow()
        ticket.closed_by = admin_id
        ticket.admin_notes = data.get("notes")

        db.commit()

        return {"status": "fechado"}, 200

    except Exception as e:
        db.rollback()
        logger.exception("Erro ao fechar ticket")
        return {"error": "erro interno"}, 500

    finally:
        db.close()


# ==============================
# CREATE ROUTE
# ==============================
@app.route("/ticket", methods=["POST"])
def create_ticket():
    data = request.get_json(silent=True)
    response, status = create_ticket_service(data)
    return jsonify(response), status


@app.route("/health")
def health():
    return {"status": "ok"}