from flask import Flask, request, jsonify
from app.database.db import SessionLocal
from app.models.ticket import Ticket
from dotenv import load_dotenv
from app.database.db import Base, engine
import os

Base.metadata.create_all(bind=engine)

load_dotenv()
app = Flask(__name__)

@app.route("/ticket", methods=["POST"])
def create_ticket():
    data = request.json
    db = SessionLocal()

    ticket = Ticket(
        user=data["user"],
        description=data["description"]
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return jsonify({"id": ticket.id, "status": ticket.status})