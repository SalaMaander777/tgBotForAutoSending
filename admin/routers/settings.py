from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import require_auth
from core.crud.settings import get_all_settings, get_setting, set_setting
from core.database import get_db

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
async def settings_form(
    request: Request,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    current_settings = await get_all_settings(session)
    return request.app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "username": username,
            "settings": current_settings,
            "success": None,
        },
    )


@router.post("/settings")
async def save_settings(
    request: Request,
    welcome_message: str = Form(default=""),
    channel_link: str = Form(default=""),
    bot_token: str = Form(default=""),
    channel_id: str = Form(default=""),
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    old_token = await get_setting(session, "bot_token") or ""
    old_channel_id = await get_setting(session, "channel_id") or ""

    await set_setting(session, "welcome_message", welcome_message)
    await set_setting(session, "channel_link", channel_link)
    await set_setting(session, "bot_token", bot_token)
    await set_setting(session, "channel_id", channel_id)

    # Restart bot if token or channel_id changed
    token_changed = bot_token and bot_token != old_token
    if token_changed:
        from admin.main import restart_bot
        try:
            await restart_bot(request.app, bot_token)
        except Exception as exc:
            current_settings = await get_all_settings(session)
            return request.app.state.templates.TemplateResponse(
                "settings.html",
                {
                    "request": request,
                    "username": username,
                    "settings": current_settings,
                    "success": None,
                    "error": f"Настройки сохранены, но перезапуск бота не удался: {exc}",
                },
            )

    current_settings = await get_all_settings(session)
    return request.app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "username": username,
            "settings": current_settings,
            "success": "Настройки сохранены" + (" — бот перезапущен" if token_changed else ""),
        },
    )
