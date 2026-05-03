from flask import Flask, request, jsonify
from app.database.db import SessionLocal, Base, engine
from app.models.ticket import Ticket
from dotenv import load_dotenv
import os
import traceback
from typing import Dict, Any, Tuple

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")


# ==============================
# 🔥 INIT DB (PROTEGIDO)
# ==============================
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Banco conectado com sucesso")
except Exception as e:
    print("❌ Erro ao conectar no banco:")
    traceback.print_exc()


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
        ticket = Ticket(
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

        print("✅ Ticket criado:", ticket.id)

        return {
            "id": ticket.id,
            "status": ticket.status
        }, 201

    except Exception:
        db.rollback()
        print("🔥 ERRO COMPLETO AO CRIAR TICKET:")
        traceback.print_exc()  # 🔥 AGORA MOSTRA O ERRO REAL

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