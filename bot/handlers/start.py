import httpx
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import channel_join_keyboard
from core.crud.settings import get_setting
from core.crud.users import mark_user_unblocked, set_user_subscribed, upsert_user

router = Router()

TRACKER_WEBHOOK_URL = "https://thedinator.com/tracker/bot/webhook/oOZ66Ig5"


async def _send_tracker_postback(user_id: int, subscriber_id: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(
                TRACKER_WEBHOOK_URL,
                params={"user_id": user_id, "subscriber_id": subscriber_id},
            )
        logger.info(f"Tracker postback sent: user_id={user_id}, subscriber_id={subscriber_id}")
    except Exception as exc:
        logger.warning(f"Tracker postback failed for user {user_id}: {exc}")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if user is None:
        return

    # Extract subscriber_id from /start <subscriber_id>
    start_args = message.text.split(maxsplit=1)
    subscriber_id = start_args[1] if len(start_args) > 1 else None
    if subscriber_id:
        await _send_tracker_postback(user.id, subscriber_id)

    await upsert_user(
        session,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        bot_token=message.bot.token,
    )

    # If user had blocked the bot before and now writes again — unblock them
    await mark_user_unblocked(session, user.id, bot_token=message.bot.token)

    welcome_text = await get_setting(session, "welcome_message")
    if not welcome_text:
        welcome_text = "Добро пожаловать!"

    # Try to create a single-use invite link for the channel
    keyboard = None
    channel_id_str = await get_setting(session, "channel_id")
    channel_id = int(channel_id_str) if channel_id_str else 0

    # Sync subscription status with the actual channel membership
    if channel_id:
        try:
            member = await message.bot.get_chat_member(chat_id=channel_id, user_id=user.id)
            is_subscribed = member.status in ("member", "administrator", "creator")
            await set_user_subscribed(session, user.id, bot_token=message.bot.token, subscribed=is_subscribed)
        except Exception as exc:
            logger.warning(f"Could not check membership for user {user.id} in channel {channel_id}: {exc}")

    if channel_id:
        try:
            link = await message.bot.create_chat_invite_link(
                chat_id=channel_id,
                member_limit=1,
            )
            keyboard = channel_join_keyboard(link.invite_link)
        except Exception as exc:
            logger.warning(f"Could not create invite link for channel {channel_id}: {exc}")
            # Fall back to stored channel link
            channel_link = await get_setting(session, "channel_link")
            if channel_link:
                keyboard = channel_join_keyboard(channel_link)

    await message.answer(welcome_text, reply_markup=keyboard)
