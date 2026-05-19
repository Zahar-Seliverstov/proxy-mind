import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path.home() / ".config" / "proxymind" / "settings.json"


class Settings(BaseModel):
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        min_length=1,
    )
    telegram_bot_token: str | None = Field(default=None, min_length=1)
    telegram_chat_id: str | None = Field(default=None, min_length=1)


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning(
            "Не удалось прочитать %s, используются значения по умолчанию.",
            path,
            exc_info=True,
        )
        return {}


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get() -> Settings:
    return Settings(**_read(SETTINGS_PATH))


def update(patch: dict[str, Any]) -> Settings:
    merged = {
        **_read(SETTINGS_PATH),
        **{k: v for k, v in patch.items() if v is not None},
    }
    settings = Settings(**merged)
    _write(SETTINGS_PATH, settings.model_dump())
    return settings
