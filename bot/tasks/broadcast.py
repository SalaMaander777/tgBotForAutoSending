import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import BufferedInputFile
from loguru import logger

from core.crud.broadcasts import update_broadcast_image_file_id, update_broadcast_stats
from core.crud.users import get_all_active_users, mark_user_blocked
from core.database import AsyncSessionLocal

BATCH_SIZE = 25
BATCH_DELAY = 1.0  # seconds between batches


async def _send_to_user(
    bot: Bot,
    chat_id: int,
    text: str | None,
    image_file_id: str | None,
    image_input: BufferedInputFile | None,
) -> str | None:
    """Send message to a single user. Returns file_id if photo was sent via BufferedInputFile."""
    returned_file_id: str | None = None

    photo = image_file_id or image_input

    if photo and text:
        sent = await bot.send_photo(chat_id=chat_id, photo=photo, caption=text)
        if image_input and sent.photo:
            returned_file_id = sent.photo[-1].file_id
    elif photo:
        sent = await bot.send_photo(chat_id=chat_id, photo=photo)
        if image_input and sent.photo:
            returned_file_id = sent.photo[-1].file_id
    elif text:
        await bot.send_message(chat_id=chat_id, text=text)

    return returned_file_id


async def run_broadcast(
    bot: Bot,
    broadcast_id: int,
    text: str | None,
    image_file_id: str | None,
    image_bytes: bytes | None = None,
    image_filename: str | None = None,
    bot_token: str | None = None,
) -> None:
    logger.info(f"Starting broadcast {broadcast_id}")
    total_sent = 0
    failed = 0

    async with AsyncSessionLocal() as session:
        users = await get_all_active_users(session, bot_token=bot_token)

    logger.info(f"Broadcast {broadcast_id}: {len(users)} users to notify")

    # Prepare BufferedInputFile once if we have raw bytes but no file_id yet
    image_input: BufferedInputFile | None = None
    if image_bytes and not image_file_id:
        image_input = BufferedInputFile(image_bytes, filename=image_filename or "image.jpg")

    for i, user in enumerate(users):
        # After first successful photo send we get a file_id and reuse it
        current_input = image_input if not image_file_id else None

        try:
            new_file_id = await _send_to_user(
                bot=bot,
                chat_id=user.telegram_id,
                text=text,
                image_file_id=image_file_id,
                image_input=current_input,
            )
            if new_file_id and not image_file_id:
                image_file_id = new_file_id
                image_input = None  # no longer needed
                async with AsyncSessionLocal() as session:
                    await update_broadcast_image_file_id(session, broadcast_id, image_file_id)
                logger.info(f"Broadcast {broadcast_id}: got file_id from first send")
            total_sent += 1
        except TelegramForbiddenError:
            logger.info(f"User {user.telegram_id} blocked the bot, marking as blocked")
            async with AsyncSessionLocal() as session:
                await mark_user_blocked(session, user.telegram_id, user.bot_token)
            failed += 1
        except TelegramRetryAfter as exc:
            logger.warning(f"Rate limited, sleeping {exc.retry_after}s")
            await asyncio.sleep(exc.retry_after)
            # Retry this user
            try:
                new_file_id = await _send_to_user(
                    bot=bot,
                    chat_id=user.telegram_id,
                    text=text,
                    image_file_id=image_file_id,
                    image_input=current_input,
                )
                if new_file_id and not image_file_id:
                    image_file_id = new_file_id
                    image_input = None
                    async with AsyncSessionLocal() as session:
                        await update_broadcast_image_file_id(session, broadcast_id, image_file_id)
                total_sent += 1
            except Exception as retry_exc:
                logger.error(f"Retry failed for user {user.telegram_id}: {retry_exc}")
                failed += 1
        except Exception as exc:
            logger.error(f"Failed to send to {user.telegram_id}: {exc}")
            failed += 1

        # Rate limiting: sleep between batches
        if (i + 1) % BATCH_SIZE == 0:
            await asyncio.sleep(BATCH_DELAY)

    # Update broadcast stats
    async with AsyncSessionLocal() as session:
        await update_broadcast_stats(session, broadcast_id, total_sent, failed)

    logger.info(f"Broadcast {broadcast_id} complete: sent={total_sent}, failed={failed}")
