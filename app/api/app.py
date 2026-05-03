from flask import Flask, request, jsonify
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
import os
import traceback
from typing import Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import func

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")


# ==============================
# 🔥 INIT DB
# ==============================
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Banco conectado com sucesso")
except Exception:
    print("❌ Erro ao conectar no banco:")
    traceback.print_exc()


# ==============================
# 🔧 GERAR CÓDIGO DO TICKET
# ==============================
def gerar_ticket_code(db, category):
    ano = datetime.now().year
    prefixo = "HW" if category == "hardware" else "SW"

    total = db.query(func.count(Ticket.id)).scalar() or 0
    numero = str(total + 1).zfill(3)

    return f"TK{prefixo}{ano}{numero}"


# ==============================
# 🔧 SERVICE LAYER
# ==============================
def create_ticket_service(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    if not isinstance(data, dict):
        return {"error": "Payload deve ser um JSON válido"}, 400

    if not data.get("user") or not data.get("description"):
        return {"error": "Campos obrigatórios: user, description"}, 400

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

        print("✅ Ticket criado:", ticket.ticket_code)

        return {
            "id": ticket.id,
            "ticket_code": ticket.ticket_code,
            "status": ticket.status
        }, 201

    except Exception:
        db.rollback()
        print("🔥 ERRO COMPLETO AO CRIAR TICKET:")
        traceback.print_exc()
        return {"error": "erro interno"}, 500

    finally:
        db.close()


# ==============================
# 🌐 ROTAS
# ==============================

@app.route("/", methods=["GET"])
def health():
    return {"status": "ok"}


@app.route("/health", methods=["GET"])
def health_alt():
    return {"status": "ok"}


@app.route("/ticket", methods=["POST"])
def create_ticket():
    data = request.get_json(silent=True)

    print("📥 Payload recebido:", data)

    response, status = create_ticket_service(data)
    return jsonify(response), status


# ==============================
# 🚀 ENTRYPOINT
# ==============================
if __name__ == "__main__":
    print("🚀 API iniciando em 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)