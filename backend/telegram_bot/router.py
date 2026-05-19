from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

import client
import config

router = APIRouter(prefix="/send", tags=["telegram"])


class MessagePayload(BaseModel):
    text: str = Field(min_length=1)


@router.post("", status_code=status.HTTP_200_OK)
async def send(payload: MessagePayload):
    settings = config.get()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан токен бота или chat_id в настройках.",
        )
    try:
        return await client.send_message(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            text=payload.text,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
