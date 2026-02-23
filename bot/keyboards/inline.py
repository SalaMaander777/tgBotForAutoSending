from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def channel_join_keyboard(invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Вступить в канал", url=invite_link)]
        ]
    )
