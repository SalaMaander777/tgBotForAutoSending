from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.user import User


async def upsert_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    user = await session.get(User, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(user)
    else:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
    await session.commit()
    await session.refresh(user)
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.get(User, telegram_id)


async def get_all_active_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.is_blocked == False))  # noqa: E712
    return list(result.scalars().all())


async def get_users_paginated(
    session: AsyncSession, offset: int = 0, limit: int = 50
) -> tuple[list[User], int]:
    count_result = await session.execute(select(func.count()).select_from(User))
    total = count_result.scalar_one()

    result = await session.execute(
        select(User).order_by(User.joined_at.desc()).offset(offset).limit(limit)
    )
    users = list(result.scalars().all())
    return users, total


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return result.scalar_one()


async def mark_user_blocked(session: AsyncSession, telegram_id: int) -> None:
    user = await session.get(User, telegram_id)
    if user:
        user.is_blocked = True
        await session.commit()


async def set_user_subscribed(session: AsyncSession, telegram_id: int, subscribed: bool) -> None:
    user = await session.get(User, telegram_id)
    if user:
        user.is_subscribed = subscribed
        await session.commit()
