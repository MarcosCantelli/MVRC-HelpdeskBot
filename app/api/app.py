from flask import Flask, request, jsonify
from flask_wtf import CSRFProtect
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import os

load_dotenv()

# 🔥 Cria tabela automaticamente
Base.metadata.create_all(bind=engine)

app = Flask(__name__)

# 🔐 SECRET KEY (obrigatório para CSRF)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

# 🧪 Ambiente de teste → desativa CSRF
if os.getenv("TEST_ENV") == "true":
    app.config["WTF_CSRF_ENABLED"] = False

# 🔐 Ativa CSRF
csrf = CSRFProtect(app)


# =========================
# 🧠 SERVICE LAYER (Sonar gosta disso)
# =========================
def create_ticket_service(data: Dict[str, Any]) -> Ticket:
    if not isinstance(data, dict):
        raise ValueError("Payload deve ser um JSON válido")

    if "user" not in data or "description" not in data:
        raise ValueError("Campos obrigatórios: user, description")

    ticket = Ticket(
        user=str(data["user"]),
        category=data.get("category"),
        subcategory=data.get("subcategory"),
        description=str(data["description"]),
        ai_suggestion=data.get("ai_suggestion"),
    )

    return ticket


# =========================
# ✅ Healthcheck
# =========================
@app.route("/", methods=["GET"])
def health():
    return {"status": "ok"}


# =========================
# 🎟️ Criar Ticket
# =========================
@csrf.exempt  # API JSON não usa CSRF token
@app.route("/ticket", methods=["POST"])
def create_ticket():
    data: Optional[Dict[str, Any]] = request.get_json()
    db = SessionLocal()

    try:
        ticket = create_ticket_service(data)

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return jsonify({
            "id": ticket.id,
            "status": ticket.status
        }), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        db.rollback()
        return jsonify({"error": "Erro interno"}), 500

    finally:
        db.close()