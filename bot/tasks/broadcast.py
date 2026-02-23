import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from loguru import logger

from core.crud.broadcasts import update_broadcast_stats
from core.crud.users import get_all_active_users, mark_user_blocked
from core.database import AsyncSessionLocal

BATCH_SIZE = 25
BATCH_DELAY = 1.0  # seconds between batches


async def run_broadcast(
    bot: Bot,
    broadcast_id: int,
    text: str | None,
    image_file_id: str | None,
) -> None:
    logger.info(f"Starting broadcast {broadcast_id}")
    total_sent = 0
    failed = 0

    async with AsyncSessionLocal() as session:
        users = await get_all_active_users(session)

    logger.info(f"Broadcast {broadcast_id}: {len(users)} users to notify")

    for i, user in enumerate(users):
        try:
            if image_file_id and text:
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=image_file_id,
                    caption=text,
                )
            elif image_file_id:
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=image_file_id,
                )
            elif text:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                )
            total_sent += 1
        except TelegramForbiddenError:
            logger.info(f"User {user.telegram_id} blocked the bot, marking as blocked")
            async with AsyncSessionLocal() as session:
                await mark_user_blocked(session, user.telegram_id)
            failed += 1
        except TelegramRetryAfter as exc:
            logger.warning(f"Rate limited, sleeping {exc.retry_after}s")
            await asyncio.sleep(exc.retry_after)
            # Retry this user
            try:
                if image_file_id and text:
                    await bot.send_photo(chat_id=user.telegram_id, photo=image_file_id, caption=text)
                elif image_file_id:
                    await bot.send_photo(chat_id=user.telegram_id, photo=image_file_id)
                elif text:
                    await bot.send_message(chat_id=user.telegram_id, text=text)
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
