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

    image_bytes: bytes | None = None
    image_filename: str | None = None
    has_image = False

    if image and image.filename:
        image_bytes = await image.read()
        image_filename = image.filename
        has_image = True

    # Determine broadcast type
    text_clean = text.strip() if text else None
    if has_image and text_clean:
        broadcast_type = "image_text"
    elif has_image:
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

    # image_file_id is unknown yet — will be set after first send in run_broadcast
    broadcast = await create_broadcast(
        session,
        type=broadcast_type,
        text=text_clean,
        image_file_id=None,
    )

    # Launch background task — image bytes are passed directly
    asyncio.create_task(
        run_broadcast(
            bot=bot,
            broadcast_id=broadcast.id,
            text=text_clean,
            image_file_id=None,
            image_bytes=image_bytes,
            image_filename=image_filename,
            bot_token=bot.token,
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
