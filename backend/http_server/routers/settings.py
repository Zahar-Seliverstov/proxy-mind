from fastapi import APIRouter, status
from pydantic import BaseModel, Field

import config

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    ollama_base_url: str | None = Field(default=None, min_length=1)
    telegram_bot_token: str | None = Field(default=None, min_length=1)
    telegram_chat_id: str | None = Field(default=None, min_length=1)


@router.get("", status_code=status.HTTP_200_OK)
def get_settings():
    return config.get()


@router.patch("", status_code=status.HTTP_200_OK)
def update_settings(patch: SettingsPatch):
    # exclude_unset (not exclude_none): an explicit null clears a field, while
    # an omitted field is left untouched. See config.update.
    return config.update(patch.model_dump(exclude_unset=True))
