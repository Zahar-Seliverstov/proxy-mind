from loguru import logger

import config
from clients.telegram import client as telegram_client


async def notify(text: str) -> None:
    settings = config.get()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    try:
        await telegram_client.send_message(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            text=text,
        )
        logger.info("Telegram-уведомление отправлено.")
    except Exception:
        logger.warning("Не удалось отправить Telegram-уведомление.")
