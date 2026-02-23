from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import require_auth
from core.crud.channel_events import get_events_paginated
from core.database import get_db

router = APIRouter()

PAGE_SIZE = 50


@router.get("/subscriptions", response_class=HTMLResponse)
async def subscriptions_list(
    request: Request,
    page: int = 1,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    offset = (page - 1) * PAGE_SIZE
    events, total = await get_events_paginated(session, offset=offset, limit=PAGE_SIZE)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    return request.app.state.templates.TemplateResponse(
        "subscriptions.html",
        {
            "request": request,
            "username": username,
            "events": events,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )
