import asyncio
from contextlib import asynccontextmanager
from typing import Any

from aiogram import Bot
from aiogram_fastapi_server import SimpleRequestHandler
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from admin.auth import login_handler, logout_handler, require_auth
from admin.routers import broadcast, dashboard, exports, settings, subscriptions, users
from bot.main import create_bot, create_dispatcher
from core.config import settings as app_settings
from core.crud.settings import get_setting, seed_defaults
from core.database import AsyncSessionLocal


class AppStateRequestHandler(SimpleRequestHandler):
    """Webhook handler that always uses app.state.bot so token changes take effect."""

    def __init__(self, app: FastAPI, **kwargs: Any) -> None:
        # Pass a dummy bot=None; we override resolve_bot and close
        super().__init__(bot=None, **kwargs)  # type: ignore[arg-type]
        self._app = app

    async def resolve_bot(self, request: Request) -> Bot:
        return self._app.state.bot

    async def close(self) -> None:
        # Session cleanup is handled by the lifespan shutdown
        pass


async def _start_bot(app: FastAPI, bot: Bot) -> None:
    """Set webhook or start polling for the given bot."""
    dp = app.state.dp
    if app_settings.bot_mode == "webhook":
        await bot.set_webhook(
            url=app_settings.webhook_url,
            secret_token=app_settings.webhook_secret,
            allowed_updates=["message", "chat_member", "callback_query"],
            drop_pending_updates=True,
        )
        logger.info(f"Webhook set to {app_settings.webhook_url}")
    else:
        polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=["message", "chat_member", "callback_query"])
        )
        app.state.polling_task = polling_task
        logger.info("Bot started in polling mode")


async def _stop_bot(app: FastAPI) -> None:
    """Stop polling / delete webhook and close current bot session."""
    bot: Bot = app.state.bot
    if app_settings.bot_mode == "webhook":
        await bot.delete_webhook()
        logger.info("Webhook deleted")
    else:
        polling_task = getattr(app.state, "polling_task", None)
        if polling_task and not polling_task.done():
            dp = app.state.dp
            await dp.stop_polling()
            # Give the polling task a moment to finish gracefully
            try:
                await asyncio.wait_for(asyncio.shield(polling_task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                polling_task.cancel()
        app.state.polling_task = None
    await bot.session.close()
    logger.info("Bot session closed")


async def restart_bot(app: FastAPI, new_token: str) -> None:
    """Stop the current bot and start a new one with new_token."""
    await _stop_bot(app)

    new_bot = create_bot(new_token)
    app.state.bot = new_bot

    await _start_bot(app, new_bot)
    logger.info("Bot restarted with new token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed default settings on startup
    async with AsyncSessionLocal() as session:
        await seed_defaults(session)
        logger.info("Default settings seeded")

        # Load bot_token from DB; fall back to .env value
        db_token = await get_setting(session, "bot_token")

    token = db_token or app_settings.bot_token

    if not token:
        logger.warning("BOT_TOKEN is not set. Configure it via /admin/settings before the bot can run.")
        app.state.bot = None
        yield
        return

    bot = create_bot(token)
    app.state.bot = bot

    await _start_bot(app, bot)

    yield

    if app.state.bot:
        await _stop_bot(app)


def create_app() -> FastAPI:
    dp = create_dispatcher()

    app = FastAPI(
        title="TG Bot Admin",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Store dp in app state (bot is set in lifespan after DB read)
    app.state.dp = dp
    app.state.bot = None
    app.state.polling_task = None

    # Templates
    templates = Jinja2Templates(directory="admin/templates")
    app.state.templates = templates

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Webhook handler (only in webhook mode)
    if app_settings.bot_mode == "webhook":
        AppStateRequestHandler(
            app=app,
            dispatcher=dp,
            secret_token=app_settings.webhook_secret,
        ).register(app, path=app_settings.webhook_path)

    # Login / logout routes
    app.add_api_route("/admin/login", _login_page, methods=["GET"])
    app.add_api_route("/admin/login", login_handler, methods=["POST"])
    app.add_api_route("/admin/logout", logout_handler, methods=["GET", "POST"])

    # Admin routers
    app.include_router(dashboard.router, prefix="/admin")
    app.include_router(users.router, prefix="/admin")
    app.include_router(broadcast.router, prefix="/admin")
    app.include_router(settings.router, prefix="/admin")
    app.include_router(exports.router, prefix="/admin")
    app.include_router(subscriptions.router, prefix="/admin")

    # Root redirect
    @app.get("/")
    async def root():
        return RedirectResponse(url="/admin/", status_code=status.HTTP_302_FOUND)

    return app


async def _login_page(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


app = create_app()
