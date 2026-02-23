from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import require_auth
from core.crud.settings import get_all_settings, set_setting
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
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    await set_setting(session, "welcome_message", welcome_message)
    await set_setting(session, "channel_link", channel_link)

    current_settings = await get_all_settings(session)
    return request.app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "username": username,
            "settings": current_settings,
            "success": "Настройки сохранены",
        },
    )
