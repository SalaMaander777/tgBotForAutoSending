from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import require_auth
from core.crud.channel_events import count_subscribed, count_unsubscribed
from core.crud.users import count_users
from core.database import get_db

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> HTMLResponse:
    total_users = await count_users(session)
    subscribed = await count_subscribed(session)
    unsubscribed = await count_unsubscribed(session)

    return request.app.state.templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": username,
            "total_users": total_users,
            "subscribed": subscribed,
            "unsubscribed": unsubscribed,
        },
    )
