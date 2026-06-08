import asyncio
import json
from typing import Any

from fastapi import WebSocket
from loguru import logger

_connections: set[WebSocket] = set()
_lock = asyncio.Lock()


async def connect(ws: WebSocket) -> None:
    async with _lock:
        _connections.add(ws)
    logger.debug("WS подключён: {} активных", len(_connections))


async def disconnect(ws: WebSocket) -> None:
    async with _lock:
        _connections.discard(ws)
    logger.debug("WS отключён: {} активных", len(_connections))


async def broadcast(data: dict[str, Any]) -> None:
    if not _connections:
        return
    msg = json.dumps(data, ensure_ascii=False)
    dead: list[WebSocket] = []
    async with _lock:
        targets = list(_connections)
    for ws in targets:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    if dead:
        async with _lock:
            for ws in dead:
                _connections.discard(ws)
