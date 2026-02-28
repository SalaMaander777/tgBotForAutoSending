from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.user import User


async def upsert_user(
    session: AsyncSession,
    telegram_id: int,
    bot_token: str,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    user = await session.get(User, (telegram_id, bot_token))
    if user is None:
        user = User(
            telegram_id=telegram_id,
            bot_token=bot_token,
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


async def get_user(session: AsyncSession, telegram_id: int, bot_token: str) -> User | None:
    return await session.get(User, (telegram_id, bot_token))


async def get_all_active_users(
    session: AsyncSession, bot_token: str | None = None
) -> list[User]:
    q = select(User).where(User.is_blocked == False)  # noqa: E712
    if bot_token:
        q = q.where(User.bot_token == bot_token)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_users_paginated(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 50,
    bot_token: str | None = None,
) -> tuple[list[User], int]:
    count_q = select(func.count()).select_from(User)
    if bot_token:
        count_q = count_q.where(User.bot_token == bot_token)
    count_result = await session.execute(count_q)
    total = count_result.scalar_one()

    q = select(User).order_by(User.joined_at.desc()).offset(offset).limit(limit)
    if bot_token:
        q = q.where(User.bot_token == bot_token)
    result = await session.execute(q)
    users = list(result.scalars().all())
    return users, total


async def count_users(session: AsyncSession, bot_token: str | None = None) -> int:
    q = select(func.count()).select_from(User)
    if bot_token:
        q = q.where(User.bot_token == bot_token)
    result = await session.execute(q)
    return result.scalar_one()


async def count_blocked(session: AsyncSession, bot_token: str | None = None) -> int:
    q = select(func.count()).select_from(User).where(User.is_blocked == True)  # noqa: E712
    if bot_token:
        q = q.where(User.bot_token == bot_token)
    result = await session.execute(q)
    return result.scalar_one()


async def mark_user_blocked(session: AsyncSession, telegram_id: int, bot_token: str) -> None:
    user = await session.get(User, (telegram_id, bot_token))
    if user:
        user.is_blocked = True
        await session.commit()


async def mark_user_unblocked(session: AsyncSession, telegram_id: int, bot_token: str) -> None:
    user = await session.get(User, (telegram_id, bot_token))
    if user and user.is_blocked:
        user.is_blocked = False
        await session.commit()


async def set_user_subscribed(
    session: AsyncSession, telegram_id: int, bot_token: str, subscribed: bool
) -> None:
    user = await session.get(User, (telegram_id, bot_token))
    if user:
        user.is_subscribed = subscribed
        await session.commit()
