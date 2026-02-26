from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.handlers import channel_events, errors, start
from bot.middlewares.db import DbSessionMiddleware


def create_bot(token: str) -> Bot:
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Register middleware on all update types
    dp.update.middleware(DbSessionMiddleware())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(channel_events.router)
    dp.include_router(errors.router)

    return dp
