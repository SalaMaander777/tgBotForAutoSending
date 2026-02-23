from contextlib import asynccontextmanager

from aiogram_fastapi_server import SimpleRequestHandler as FastAPIRequestHandler
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from admin.auth import login_handler, logout_handler, require_auth
from admin.routers import broadcast, dashboard, exports, settings, subscriptions, users
from bot.main import create_bot, create_dispatcher
from core.config import settings as app_settings
from core.crud.settings import seed_defaults
from core.database import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed default settings on startup
    async with AsyncSessionLocal() as session:
        await seed_defaults(session)
        logger.info("Default settings seeded")

    bot = app.state.bot
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
        # Polling mode — start polling in background
        import asyncio
        polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=["message", "chat_member", "callback_query"])
        )
        app.state.polling_task = polling_task
        logger.info("Bot started in polling mode")

    yield

    # Shutdown
    if app_settings.bot_mode == "webhook":
        await bot.delete_webhook()
        logger.info("Webhook deleted")
    else:
        if hasattr(app.state, "polling_task"):
            app.state.polling_task.cancel()
            try:
                await app.state.polling_task
            except Exception:
                pass

    await bot.session.close()
    logger.info("Bot session closed")


def create_app() -> FastAPI:
    bot = create_bot()
    dp = create_dispatcher()

    app = FastAPI(
        title="TG Bot Admin",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Store bot and dp in app state
    app.state.bot = bot
    app.state.dp = dp

    # Templates
    templates = Jinja2Templates(directory="admin/templates")
    app.state.templates = templates

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Webhook handler (only in webhook mode)
    if app_settings.bot_mode == "webhook":
        FastAPIRequestHandler(
            dispatcher=dp,
            bot=bot,
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
