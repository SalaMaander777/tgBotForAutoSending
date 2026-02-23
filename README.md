# Telegram Bot + FastAPI Admin Panel

A Telegram bot with a web-based admin panel for managing subscribers and sending broadcasts to a channel.

## Features

- **Subscription tracking** — tracks when users subscribe/unsubscribe from a Telegram channel
- **Broadcast system** — send text or image messages to all subscribers with rate limiting
- **Admin panel** — web UI for managing users, broadcasts, and settings
- **Invite links** — auto-generates personal invite links for new users
- **Export** — download user list as CSV

## Stack

- [aiogram 3.17](https://docs.aiogram.dev/) — Telegram bot framework
- [FastAPI 0.115](https://fastapi.tiangolo.com/) — admin panel backend
- [SQLAlchemy 2 + asyncpg](https://docs.sqlalchemy.org/) — async PostgreSQL ORM
- [Alembic](https://alembic.sqlalchemy.org/) — database migrations
- [Jinja2](https://jinja.palletsprojects.com/) — HTML templates
- [Docker + Nginx](https://www.docker.com/) — containerized deployment

## Quick Start

### Requirements

- Docker & Docker Compose
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Bot must be **admin** in the target channel

### Development (polling mode)

```bash
cp .env.example .env
# Edit .env — fill in BOT_TOKEN, CHANNEL_ID, DATABASE_URL, ADMIN_PASSWORD_HASH
python scripts/create_admin.py  # generates ADMIN_PASSWORD_HASH
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Admin panel will be available at: http://localhost:8000/admin

### Production (webhook mode)

```bash
cp .env.example .env
# Edit .env — fill in all variables including WEBHOOK_BASE_URL
docker-compose up -d
```

### Run without Docker

```bash
pip install -e .
python -m uvicorn admin.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `BOT_MODE` | `webhook` (prod) or `polling` (dev) |
| `WEBHOOK_BASE_URL` | Public HTTPS URL for webhook (prod only) |
| `CHANNEL_ID` | Telegram channel ID (negative number, e.g. `-1001234567890`) |
| `DATABASE_URL` | PostgreSQL asyncpg URL (e.g. `postgresql+asyncpg://user:pass@host/db`) |
| `ADMIN_USERNAME` | Admin panel login |
| `ADMIN_PASSWORD_HASH` | bcrypt hash — generate with `python scripts/create_admin.py` |
| `SECRET_KEY` | Cookie signing secret (random 32+ character string) |

## Project Structure

```
├── bot/
│   ├── handlers/         # Telegram update handlers
│   ├── middlewares/      # DB session middleware
│   ├── keyboards/        # Inline keyboards
│   └── tasks/            # Background tasks (broadcast)
├── admin/
│   ├── routers/          # FastAPI route handlers
│   ├── templates/        # Jinja2 HTML templates
│   └── auth.py           # Session-based authentication
├── core/
│   ├── models/           # SQLAlchemy ORM models
│   ├── crud/             # Database operations
│   ├── config.py         # Settings via pydantic-settings
│   └── database.py       # Async engine + session factory
├── migrations/           # Alembic migrations
├── scripts/
│   └── create_admin.py   # Generate bcrypt password hash
├── static/css/           # Admin panel styles
└── docker/               # Dockerfile + nginx config
```

## Database Models

| Model | Description |
|-------|-------------|
| `users` | Telegram users who started the bot |
| `channel_events` | Subscribe/unsubscribe events per user |
| `settings` | Key-value config (welcome message, channel link) |
| `broadcasts` | Broadcast history with delivery stats |

## Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"
```

## Architecture Notes

- **Single process**: bot (aiogram) + admin panel (FastAPI) run together in one uvicorn process
- **Broadcast rate limit**: 25 messages per batch, 1 second between batches (stays under Telegram's 30/s limit)
- **Image broadcasts**: image is uploaded once to get a `file_id`, then reused for all recipients
- **Auth**: cookie-based session using `itsdangerous.TimestampSigner` + bcrypt password verification
