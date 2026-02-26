from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import channel_join_keyboard
from core.crud.settings import get_setting
from core.crud.users import upsert_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if user is None:
        return

    await upsert_user(
        session,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    welcome_text = await get_setting(session, "welcome_message")
    if not welcome_text:
        welcome_text = "Добро пожаловать!"

    # Try to create a single-use invite link for the channel
    keyboard = None
    channel_id_str = await get_setting(session, "channel_id")
    channel_id = int(channel_id_str) if channel_id_str else 0
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
