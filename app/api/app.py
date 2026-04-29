from flask import Flask, request, jsonify
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
import os
from typing import Dict, Any, Tuple

load_dotenv()

# 🔥 Cria tabela automaticamente
Base.metadata.create_all(bind=engine)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")


# ==============================
# 🔧 SERVICE LAYER
# ==============================
def create_ticket_service(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    if not isinstance(data, dict):
        return {"error": "Payload deve ser um JSON válido"}, 400

    if "user" not in data or "description" not in data:
        return {"error": "Dados inválidos"}, 400

    db = SessionLocal()

    try:
        ticket = Ticket(
            user=data["user"],
            category=data.get("category"),
            subcategory=data.get("subcategory"),
            description=data["description"],
            ai_suggestion=data.get("ai_suggestion"),
            status="aberto"  # 🔥 garante valor correto
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return {
            "id": ticket.id,
            "status": ticket.status
        }, 201

    except Exception as e:
        db.rollback()
        return {"error": str(e)}, 500

    finally:
        db.close()


# ==============================
# 🌐 ROTAS
# ==============================
@app.route("/", methods=["GET"])
def health():
    return {"status": "ok"}


@app.route("/ticket", methods=["POST"])
def create_ticket():
    data = request.json
    response, status = create_ticket_service(data)
    return jsonify(response), status


# ==============================
# 🚀 ENTRYPOINT
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)