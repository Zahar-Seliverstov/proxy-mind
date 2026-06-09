"""Загрузка и сохранение настроек через таблицу settings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database.models import Setting


async def load_settings(session: AsyncSession) -> None:
    """Загружает настройки из БД в config-кэш."""
    rows = (await session.execute(select(Setting))).scalars().all()
    raw = {r.key: r.value for r in rows}
    config._set_cache(config.Settings(**{k: v for k, v in raw.items() if v is not None}))


async def save_settings(session: AsyncSession, patch: dict) -> config.Settings:
    """Записывает изменённые настройки в БД и обновляет кэш."""
    for key, value in patch.items():
        row = await session.get(Setting, key)
        if row is not None:
            row.value = str(value) if value is not None else None
        else:
            session.add(Setting(key=key, value=str(value) if value is not None else None))
    await session.commit()
    updated = config.update(patch)
    return updated
