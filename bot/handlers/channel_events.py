from aiogram import Router
from aiogram.filters.chat_member_updated import (
    IS_MEMBER,
    IS_NOT_MEMBER,
    ChatMemberUpdatedFilter,
)
from aiogram.types import ChatMemberUpdated
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from core.crud.channel_events import create_event
from core.crud.users import set_user_subscribed, upsert_user

router = Router()


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_subscribed(event: ChatMemberUpdated, session: AsyncSession) -> None:
    user = event.new_chat_member.user
    logger.info(f"User {user.id} subscribed to channel")

    # Ensure user exists in DB (they might not have started the bot yet)
    await upsert_user(
        session,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        bot_token=event.bot.token,
    )
    await set_user_subscribed(session, user.id, bot_token=event.bot.token, subscribed=True)
    await create_event(session, user_id=user.id, event_type="subscribed")


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_unsubscribed(event: ChatMemberUpdated, session: AsyncSession) -> None:
    user = event.new_chat_member.user
    logger.info(f"User {user.id} unsubscribed from channel")

    await upsert_user(
        session,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        bot_token=event.bot.token,
    )
    await set_user_subscribed(session, user.id, bot_token=event.bot.token, subscribed=False)
    await create_event(session, user_id=user.id, event_type="unsubscribed")
