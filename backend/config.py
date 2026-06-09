"""
Настройки приложения.

Источник истины — таблица settings в БД (инициализируется при старте).
get() и update() работают синхронно через in-memory кэш,
поэтому существующий код (ollama-клиент, notifications) не требует изменений.
"""

from pydantic import BaseModel, Field


class Settings(BaseModel):
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        min_length=1,
    )
    telegram_bot_token: str | None = Field(default=None, min_length=1)
    telegram_chat_id: str | None = Field(default=None, min_length=1)


# In-memory кэш — заполняется через load_from_db() при старте
_cache: Settings = Settings()


def get() -> Settings:
    return _cache


def update(patch: dict) -> Settings:
    global _cache
    data = _cache.model_dump()
    data.update({k: v for k, v in patch.items() if v is not None})
    _cache = Settings(**data)
    return _cache


def _set_cache(settings: Settings) -> None:
    """Вызывается из database/config_db.py после загрузки из БД."""
    global _cache
    _cache = settings
