from flask import Flask, request, jsonify
from flask_wtf import CSRFProtect
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
import os

load_dotenv()

# 🔥 Cria tabela automaticamente
Base.metadata.create_all(bind=engine)

app = Flask(__name__)

# 🔐 IMPORTANTE: chave para CSRF
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

# 🔐 Ativa proteção CSRF
csrf = CSRFProtect(app)


# ✅ Healthcheck
@app.route("/", methods=["GET"])
def health():
    return {"status": "ok"}


# ⚠️ API normalmente usa JSON → precisa liberar CSRF aqui
@csrf.exempt
@app.route("/ticket", methods=["POST"])
def create_ticket():
    data = request.json
    db = SessionLocal()

    try:
        if not data or "user" not in data or "description" not in data:
            return jsonify({"error": "Dados inválidos"}), 400

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