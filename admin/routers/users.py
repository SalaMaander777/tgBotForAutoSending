from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import BufferedInputFile
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import require_auth
from core.config import settings as app_settings
from core.crud.settings import get_setting
from core.crud.users import get_user, get_users_paginated, mark_user_blocked, mark_user_unblocked
from core.database import get_db

router = APIRouter()

PAGE_SIZE = 50


@router.get("/users", response_class=HTMLResponse)
async def users_list(
    request: Request,
    page: int = 1,
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    if status not in ("active", "blocked"):
        status = None
    offset = (page - 1) * PAGE_SIZE
    bot_token = await get_setting(session, "bot_token") or app_settings.bot_token or None
    users, total = await get_users_paginated(
        session, offset=offset, limit=PAGE_SIZE, bot_token=bot_token, status=status
    )
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    return request.app.state.templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "username": username,
            "users": users,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "status_filter": status,
        },
    )


@router.post("/users/{user_id}/toggle-block")
async def toggle_user_block(
    request: Request,
    user_id: int,
    bot_token: str,
    page: int = 1,
    status_filter: str | None = None,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> RedirectResponse:
    user = await get_user(session, user_id, bot_token)
    if user is not None:
        bot: Bot = request.app.state.bot
        channel_id_str = await get_setting(session, "channel_id")
        channel_id = int(channel_id_str) if channel_id_str else None

        if user.is_blocked:
            await mark_user_unblocked(session, user_id, bot_token)
            if channel_id:
                try:
                    await bot.unban_chat_member(chat_id=channel_id, user_id=user_id, only_if_banned=True)
                except Exception:
                    pass
        else:
            await mark_user_blocked(session, user_id, bot_token)
            if channel_id:
                try:
                    await bot.ban_chat_member(chat_id=channel_id, user_id=user_id)
                except Exception:
                    pass

    redirect_url = f"/admin/users?page={page}"
    if status_filter:
        redirect_url += f"&status={status_filter}"
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/users/{user_id}/message", response_class=HTMLResponse)
async def user_message_form(
    request: Request,
    user_id: int,
    bot_token: str,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    user = await get_user(session, user_id, bot_token)
    if user is None:
        return HTMLResponse("Пользователь не найден", status_code=404)

    return request.app.state.templates.TemplateResponse(
        "user_message.html",
        {
            "request": request,
            "username": username,
            "user": user,
            "success": None,
            "error": None,
        },
    )


@router.post("/users/{user_id}/message")
async def send_user_message(
    request: Request,
    user_id: int,
    bot_token: str,
    text: str = Form(default=""),
    image: UploadFile = File(default=None),
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    user = await get_user(session, user_id, bot_token)
    if user is None:
        return HTMLResponse("Пользователь не найден", status_code=404)

    bot: Bot = request.app.state.bot
    success = None
    error = None

    text_clean = text.strip() if text else None
    has_image = image and image.filename

    if not text_clean and not has_image:
        error = "Введите текст или прикрепите фото"
        return request.app.state.templates.TemplateResponse(
            "user_message.html",
            {
                "request": request,
                "username": username,
                "user": user,
                "success": None,
                "error": error,
            },
        )

    input_file: BufferedInputFile | None = None
    if has_image:
        image_bytes = await image.read()
        input_file = BufferedInputFile(image_bytes, filename=image.filename)

    if not error:
        try:
            if input_file and text_clean:
                await bot.send_photo(chat_id=user_id, photo=input_file, caption=text_clean, parse_mode="HTML")
            elif input_file:
                await bot.send_photo(chat_id=user_id, photo=input_file)
            else:
                await bot.send_message(chat_id=user_id, text=text_clean, parse_mode="HTML")
            success = "Сообщение успешно отправлено"
        except TelegramForbiddenError:
            await mark_user_blocked(session, user_id, bot_token)
            error = "Пользователь заблокировал бота"
        except TelegramBadRequest as exc:
            error = f"Ошибка Telegram: {exc.message}"
        except Exception as exc:
            error = f"Ошибка: {exc}"

    return request.app.state.templates.TemplateResponse(
        "user_message.html",
        {
            "request": request,
            "username": username,
            "user": user,
            "success": success,
            "error": error,
        },
    )
