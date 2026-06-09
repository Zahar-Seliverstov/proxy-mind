from fastapi import APIRouter, status

from pydantic import BaseModel, Field

import config
from database.config_db import save_settings
from database.db import SessionLocal

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    ollama_base_url: str | None = Field(default=None, min_length=1)
    telegram_bot_token: str | None = Field(default=None, min_length=1)
    telegram_chat_id: str | None = Field(default=None, min_length=1)


@router.get("", status_code=status.HTTP_200_OK)
def get_settings():
    return config.get()


@router.patch("", status_code=status.HTTP_200_OK)
async def update_settings(patch: SettingsPatch):
    async with SessionLocal() as session:
        return await save_settings(session, patch.model_dump(exclude_unset=True))
