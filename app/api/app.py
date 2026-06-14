from flask import Flask, request, jsonify
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
import os
import logging
from typing import Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import func

logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)


def utcnow():
    return datetime.now(timezone.utc)

def get_admin_ids():
    raw = os.getenv("ADMIN_IDS", "")
    fallback = os.getenv("TELEGRAM_ADMIN_ID", "") or os.getenv("TELEGRAM_ADMIN_IDS", "")
    ids = []
    for value in (raw, fallback):
        for item in value.split(","):
            candidate = item.strip()
            if candidate:
                ids.append(candidate)
    return list(dict.fromkeys(ids))


ADMIN_IDS = get_admin_ids()

# ==============================
# INIT DB
# ==============================
def init_db():
    try:
        logger.info("Inicializando banco de dados")

        # garante carregamento do model
        from app.models.ticket import Ticket

        Base.metadata.create_all(bind=engine)

        logger.info("Banco inicializado com sucesso")

    except Exception:
        logger.exception("Erro ao inicializar banco de dados")
        raise
    
# ==============================
# GERAR CÓDIGO
# ==============================
def gerar_ticket_code(db, category):
    ano = datetime.now(timezone.utc).year

    total = db.query(func.count(Ticket.id)).scalar() or 0
    numero = str(total + 1).zfill(3)

    return f"TK{ano}{numero}"


# ==============================
# CREATE
# ==============================
def create_ticket_service(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    if not data or not data.get("user") or not data.get("description"):
        return {"error": "Campos obrigatórios"}, 400

    init_db()
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
            status="aberto",
            chat_id=data.get("chat_id")
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
# BUSCAR TICKET POR CÓDIGO
# ==============================
@app.route("/ticket/<ticket_code>", methods=["GET"])
def get_ticket_by_code(ticket_code):
    db = SessionLocal()

    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()

        if not ticket:
            return {"error": "not found"}, 404

        return {
            "id": ticket.id,
            "code": ticket.ticket_code,
            "user": ticket.user,
            "category": ticket.category,
            "subcategory": ticket.subcategory,
            "description": ticket.description,
            "ai_suggestion": ticket.ai_suggestion,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "closed_at": ticket.closed_at,
            "chat_id": ticket.chat_id,
            "admin_notes": ticket.admin_notes
        }, 200

    except Exception as e:
        logger.exception("Erro ao buscar ticket")
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
        init_db()
        db = SessionLocal()
        tickets = db.query(Ticket).all()

        return jsonify([
            {
                "id": t.id,
                "code": t.ticket_code,
                "user": t.user,
                "status": t.status,
                "created_at": t.created_at,
                "closed_at": t.closed_at,
                "chat_id": t.chat_id,
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
        ticket.closed_at = utcnow()
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
# ALTERAR STATUS TICKET
# ==============================
@app.route("/ticket/<int:ticket_id>/status", methods=["PATCH"])
def update_ticket_status(ticket_id):
    data = request.get_json() or {}
    admin_id = str(data.get("admin"))

    if admin_id not in ADMIN_IDS:
        return {"error": "não autorizado"}, 403

    db = SessionLocal()

    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

        if not ticket:
            return {"error": "not found"}, 404

        new_status = data.get("status")
        if new_status not in ["aberto", "em atendimento", "encerrado"]:
            return {"error": "status inválido"}, 400

        ticket.status = new_status
        if new_status == "encerrado":
            ticket.closed_at = utcnow()
            ticket.closed_by = admin_id

        db.commit()

        return {"status": new_status}, 200

    except Exception as e:
        db.rollback()
        logger.exception("Erro ao alterar status")
        return {"error": "erro interno"}, 500

    finally:
        db.close()


# ==============================
# ADICIONAR OBSERVAÇÃO
# ==============================
@app.route("/ticket/<int:ticket_id>/note", methods=["POST"])
def add_ticket_note(ticket_id):
    data = request.get_json() or {}
    admin_id = str(data.get("admin"))
    note = data.get("note")

    if admin_id not in ADMIN_IDS:
        return {"error": "não autorizado"}, 403

    if not note:
        return {"error": "observação obrigatória"}, 400

    db = SessionLocal()

    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

        if not ticket:
            return {"error": "not found"}, 404

        # Adicionar à admin_notes existente
        existing_notes = ticket.admin_notes or ""
        if existing_notes:
            existing_notes += "\n"
        ticket.admin_notes = existing_notes + f"{utcnow()}: {note}"

        db.commit()

        return {"message": "observação adicionada"}, 200

    except Exception as e:
        db.rollback()
        logger.exception("Erro ao adicionar observação")
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


if __name__ == "__main__":
    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )