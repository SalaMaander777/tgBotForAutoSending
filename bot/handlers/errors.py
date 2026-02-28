from aiogram import Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import ErrorEvent
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from core.crud.users import mark_user_blocked

router = Router()


@router.errors()
async def global_error_handler(event: ErrorEvent, session: AsyncSession) -> None:
    if isinstance(event.exception, TelegramForbiddenError):
        # Try to extract telegram_id and bot_token from the update
        update = event.update
        telegram_id: int | None = None
        bot_token: str | None = None

        for attr in ("message", "callback_query", "inline_query", "my_chat_member"):
            obj = getattr(update, attr, None)
            if obj is None:
                continue
            from_user = getattr(obj, "from_user", None)
            if from_user:
                telegram_id = from_user.id
            bot = getattr(obj, "bot", None)
            if bot:
                bot_token = bot.token
            if telegram_id and bot_token:
                break

        if telegram_id and bot_token:
            await mark_user_blocked(session, telegram_id, bot_token)
            logger.info(f"User {telegram_id} blocked the bot — marked as blocked")
        else:
            logger.warning(f"TelegramForbiddenError but could not identify user: {event.exception}")
    else:
        logger.error(
            f"Unhandled error: {event.exception}",
            exc_info=event.exception,
        )
