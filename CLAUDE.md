# Project: Telegram Bot + FastAPI Admin Panel

## Quick Start

### Development (polling mode)
```bash
cp .env.example .env
# Edit .env: set BOT_TOKEN, CHANNEL_ID, DATABASE_URL, ADMIN_PASSWORD_HASH
python scripts/create_admin.py  # generates password hash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Production (webhook mode)
```bash
cp .env.example .env
# Edit .env: set all values including WEBHOOK_BASE_URL
docker-compose up -d
```

## Architecture

- **Single process**: bot (aiogram) + admin panel (FastAPI) run in one uvicorn process
- **Bot mode**: `BOT_MODE=webhook` (prod) or `BOT_MODE=polling` (dev)
- **Admin auth**: cookie session via itsdangerous + bcrypt password check
- **Broadcast**: asyncio background task, 25 msgs/batch with 1s delay

## Key Files

| File | Purpose |
|------|---------|
| `core/config.py` | All settings via pydantic-settings |
| `core/database.py` | Async SQLAlchemy engine + session factory |
| `admin/main.py` | FastAPI app factory, mounts bot webhook |
| `bot/main.py` | Bot + dispatcher factory |
| `scripts/create_admin.py` | Generate bcrypt hash for admin password |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `BOT_MODE` | `webhook` or `polling` |
| `WEBHOOK_BASE_URL` | Public HTTPS URL (prod only) |
| `CHANNEL_ID` | Telegram channel ID (negative number) |
| `DATABASE_URL` | PostgreSQL asyncpg URL |
| `ADMIN_USERNAME` | Admin login username |
| `ADMIN_PASSWORD_HASH` | bcrypt hash (use scripts/create_admin.py) |
| `SECRET_KEY` | Cookie signing key (random 32+ chars) |

## Database Models

- `users` — Telegram users who started the bot
- `channel_events` — subscribe/unsubscribe events
- `settings` — key-value config (welcome_message, channel_link)
- `broadcasts` — broadcast history with stats

## Migrations

```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## Notes

- Bot must be admin in the channel to create invite links and track member events
- `allowed_updates` must include `chat_member` for subscription tracking
- Broadcast rate limit: 25 msgs per batch, 1s between batches (stays under 30/s)
- Image broadcasts: upload once → store file_id → reuse (no re-upload)
