from sqlalchemy.ext.asyncio import AsyncSession

from core.models.setting import Setting

DEFAULT_SETTINGS = {
    "welcome_message": "Добро пожаловать! Нажмите кнопку ниже, чтобы вступить в канал.",
    "channel_link": "",
    "bot_token": "",
    "channel_id": "",
}


async def get_setting(session: AsyncSession, key: str) -> str | None:
    setting = await session.get(Setting, key)
    return setting.value if setting else None


async def set_setting(session: AsyncSession, key: str, value: str) -> Setting:
    setting = await session.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value=value)
        session.add(setting)
    else:
        setting.value = value
    await session.commit()
    await session.refresh(setting)
    return setting


async def get_all_settings(session: AsyncSession) -> dict[str, str]:
    from sqlalchemy import select
    result = await session.execute(select(Setting))
    return {s.key: s.value for s in result.scalars().all()}


async def seed_defaults(session: AsyncSession) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        existing = await session.get(Setting, key)
        if existing is None:
            session.add(Setting(key=key, value=value))
    await session.commit()
