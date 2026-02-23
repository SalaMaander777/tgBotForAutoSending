from aiogram import Router
from aiogram.types import ErrorEvent
from loguru import logger

router = Router()


@router.errors()
async def global_error_handler(event: ErrorEvent) -> None:
    logger.error(
        f"Unhandled error: {event.exception}",
        exc_info=event.exception,
    )
