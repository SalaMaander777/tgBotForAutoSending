import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import require_auth
from core.crud.users import get_users_paginated
from core.database import get_db

router = APIRouter()


@router.get("/export/users.csv")
async def export_users(
    session: AsyncSession = Depends(get_db),
    username: str = Depends(require_auth),
) -> StreamingResponse:
    # Fetch all users (large offset/limit to get all)
    users, total = await get_users_paginated(session, offset=0, limit=100_000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["telegram_id", "username", "first_name", "last_name", "joined_at", "is_blocked"])

    for user in users:
        writer.writerow([
            user.telegram_id,
            user.username or "",
            user.first_name or "",
            user.last_name or "",
            user.joined_at.isoformat() if user.joined_at else "",
            user.is_blocked,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )
