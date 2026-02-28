import bcrypt

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import get_admin_password_hash, require_auth, verify_password
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
    pw_success = request.query_params.get("pw_success")
    pw_error = request.query_params.get("pw_error")
    return request.app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "username": username,
            "settings": current_settings,
            "success": None,
            "pw_success": pw_success,
            "pw_error": pw_error,
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


@router.post("/settings/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    session: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> RedirectResponse:
    if new_password != confirm_password:
        return RedirectResponse(
            url="/admin/settings?pw_error=Новый+пароль+и+подтверждение+не+совпадают",
            status_code=302,
        )
    if len(new_password) < 8:
        return RedirectResponse(
            url="/admin/settings?pw_error=Новый+пароль+должен+быть+не+короче+8+символов",
            status_code=302,
        )
    current_hash = await get_admin_password_hash(session)
    if not current_hash or not verify_password(current_password, current_hash):
        return RedirectResponse(
            url="/admin/settings?pw_error=Неверный+текущий+пароль",
            status_code=302,
        )
    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    await set_setting(session, "admin_password_hash", new_hash)
    return RedirectResponse(
        url="/admin/settings?pw_success=1",
        status_code=302,
    )
