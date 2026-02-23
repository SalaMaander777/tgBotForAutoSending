import asyncio

from aiogram import Bot
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import require_auth
from bot.tasks.broadcast import run_broadcast
from core.crud.broadcasts import create_broadcast, get_broadcasts
from core.database import get_db

router = APIRouter()


@router.get("/broadcast", response_class=HTMLResponse)
async def broadcast_form(
    request: Request,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    broadcasts = await get_broadcasts(session)
    return request.app.state.templates.TemplateResponse(
        "broadcast.html",
        {
            "request": request,
            "username": username,
            "broadcasts": broadcasts,
            "success": None,
            "error": None,
        },
    )


@router.post("/broadcast")
async def send_broadcast(
    request: Request,
    text: str = Form(default=""),
    image: UploadFile = File(default=None),
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    bot: Bot = request.app.state.bot

    image_file_id: str | None = None
    error: str | None = None

    # Upload image if provided to get a permanent file_id
    if image and image.filename:
        try:
            from aiogram.types import BufferedInputFile
            from core.config import settings as app_settings

            image_bytes = await image.read()
            input_file = BufferedInputFile(image_bytes, filename=image.filename)

            # Send to the channel to get a file_id, then delete
            upload_chat = app_settings.channel_id
            sent = await bot.send_photo(chat_id=upload_chat, photo=input_file)
            try:
                await bot.delete_message(chat_id=upload_chat, message_id=sent.message_id)
            except Exception:
                pass  # Deletion failure is non-critical
            if sent.photo:
                image_file_id = sent.photo[-1].file_id
        except Exception as exc:
            error = f"Ошибка загрузки изображения: {exc}"

    if error:
        broadcasts = await get_broadcasts(session)
        return request.app.state.templates.TemplateResponse(
            "broadcast.html",
            {
                "request": request,
                "username": username,
                "broadcasts": broadcasts,
                "success": None,
                "error": error,
            },
        )

    # Determine broadcast type
    text_clean = text.strip() if text else None
    if image_file_id and text_clean:
        broadcast_type = "image_text"
    elif image_file_id:
        broadcast_type = "image"
    elif text_clean:
        broadcast_type = "text"
    else:
        broadcasts = await get_broadcasts(session)
        return request.app.state.templates.TemplateResponse(
            "broadcast.html",
            {
                "request": request,
                "username": username,
                "broadcasts": broadcasts,
                "success": None,
                "error": "Необходимо указать текст или изображение",
            },
        )

    broadcast = await create_broadcast(
        session,
        type=broadcast_type,
        text=text_clean,
        image_file_id=image_file_id,
    )

    # Launch background task
    asyncio.create_task(
        run_broadcast(
            bot=bot,
            broadcast_id=broadcast.id,
            text=text_clean,
            image_file_id=image_file_id,
        )
    )

    broadcasts = await get_broadcasts(session)
    return request.app.state.templates.TemplateResponse(
        "broadcast.html",
        {
            "request": request,
            "username": username,
            "broadcasts": broadcasts,
            "success": f"Рассылка #{broadcast.id} запущена",
            "error": None,
        },
    )
