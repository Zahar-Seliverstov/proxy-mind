import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path.home() / ".config" / "proxymind" / "settings.json"


class Settings(BaseModel):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


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


def get() -> Settings:
    return Settings(**_read(SETTINGS_PATH))
