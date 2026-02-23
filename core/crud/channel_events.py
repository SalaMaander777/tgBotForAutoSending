from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.models.channel_event import ChannelEvent


async def create_event(
    session: AsyncSession,
    user_id: int,
    event_type: str,
) -> ChannelEvent:
    event = ChannelEvent(user_id=user_id, event_type=event_type)
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def get_events_paginated(
    session: AsyncSession, offset: int = 0, limit: int = 50
) -> tuple[list[ChannelEvent], int]:
    count_result = await session.execute(select(func.count()).select_from(ChannelEvent))
    total = count_result.scalar_one()

    result = await session.execute(
        select(ChannelEvent)
        .options(joinedload(ChannelEvent.user))
        .order_by(ChannelEvent.occurred_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events = list(result.scalars().all())
    return events, total


async def count_subscribed(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).select_from(ChannelEvent).where(ChannelEvent.event_type == "subscribed")
    )
    return result.scalar_one()


async def count_unsubscribed(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).select_from(ChannelEvent).where(ChannelEvent.event_type == "unsubscribed")
    )
    return result.scalar_one()
