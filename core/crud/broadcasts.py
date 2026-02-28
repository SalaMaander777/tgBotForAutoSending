from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.broadcast import Broadcast


async def create_broadcast(
    session: AsyncSession,
    type: str,
    text: str | None = None,
    image_file_id: str | None = None,
) -> Broadcast:
    broadcast = Broadcast(type=type, text=text, image_file_id=image_file_id)
    session.add(broadcast)
    await session.commit()
    await session.refresh(broadcast)
    return broadcast


async def update_broadcast_stats(
    session: AsyncSession,
    broadcast_id: int,
    total_sent: int,
    failed: int,
) -> None:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast:
        broadcast.total_sent = total_sent
        broadcast.failed = failed
        await session.commit()


async def update_broadcast_image_file_id(
    session: AsyncSession,
    broadcast_id: int,
    image_file_id: str,
) -> None:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast:
        broadcast.image_file_id = image_file_id
        await session.commit()


async def get_broadcasts(session: AsyncSession, limit: int = 20) -> list[Broadcast]:
    result = await session.execute(
        select(Broadcast).order_by(Broadcast.sent_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
