# MVRC-HelpdeskBot

A helpdesk solution with a Telegram bot and REST API for ticket management. The project is prepared to run on a Raspberry Pi and validated in a Jenkins pipeline with tests and coverage.

## Overview

- `app/api/app.py` — Flask API for creating, listing, and closing tickets.
- `app/bot/bot.py` — Telegram bot using `python-telegram-bot` to interact with users and create tickets via the API.
- `app/database/db.py` — SQLAlchemy configuration with `TEST_ENV` support for in-memory tests.
- `app/models/ticket.py` — Ticket data model.

## Architecture

1. A user interacts with the Telegram bot.
2. The bot collects category, equipment, and problem description.
3. If the issue is simple, the bot replies with a suggested fix.
4. Otherwise, the bot creates a ticket through the REST API.
5. The API persists the ticket in the database and returns the ticket code.
6. Administrators can list and close tickets via bot commands or API endpoints.

## Project structure

- `app/`
  - `api/` — Flask API application.
  - `bot/` — Telegram bot logic.
  - `database/` — SQLAlchemy engine and session.
  - `models/` — Ticket model.
- `tests/` — full unit and integration test suite.
- `Dockerfile.api` — API container image.
- `Dockerfile.bot` — bot container image.
- `docker-compose.yml` — orchestrates API and bot services.
- `requirements.txt` — Python dependencies.

## Requirements

- Python 3.10+
- Docker / Docker Compose (for Raspberry Pi deployment)
- Jenkins (for CI pipeline)

## Environment variables

### API

- `DATABASE_URL` — database URL for PostgreSQL or SQLite.
- `ADMIN_IDS` — comma-separated list of valid admin IDs.

### Bot

- `TELEGRAM_TOKEN` — Telegram bot token.
- `TELEGRAM_CHAT_ID` — chat ID for notifications and optional admin ID.
- `API_URL` — API URL (default: `http://helpdesk-api:5000`).
- `ADMIN_IDS` — comma-separated list of valid admin IDs.

## Running locally

### Create Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Run API

```bash
export DATABASE_URL="sqlite:///helpdesk.db"
export ADMIN_IDS="123,456"
python -m app.api.app
```

### Run bot

```bash
export TELEGRAM_TOKEN="<your-token>"
export TELEGRAM_CHAT_ID="<your-chat-id>"
export API_URL="http://localhost:5000"
export ADMIN_IDS="123,456"
python -m app.bot.bot
```

## Docker / Raspberry Pi

The project already includes `Dockerfile.api` and `Dockerfile.bot` prepared for lightweight environments like Raspberry Pi.

### Using Docker Compose

```bash
docker compose build
docker compose up -d
```

### Raspberry Pi environment variables

Set them in a `.env` file or in Docker Compose environment:

- `DATABASE_URL`
- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`
- `ADMIN_IDS`
- `ADMIN_CHAT_ID` (for the bot container if needed)

## Jenkins pipeline

The pipeline should create a venv, install dependencies, and run tests with coverage:

```bash
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio
export PYTHONPATH=$(pwd)
export TEST_ENV=true
pytest --cov=app --cov-report=xml:coverage.xml
```

## Tests

- The database uses `TEST_ENV=true` to enable `sqlite:///:memory:` during tests.
- The full suite currently passes with `90 passed`.

## Notes

- The bot uses message flows and commands `/start`, `/tickets`, and `/close`.
- The API exposes routes to create a ticket (`POST /ticket`), list tickets (`GET /tickets`), and close a ticket (`POST /ticket/<id>/close`).
- The project is organized for maintainability and extensibility.
