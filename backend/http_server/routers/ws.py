from fastapi import APIRouter, WebSocket

from services import ws_hub
from services import orchestrator
from services.tmux import sessions as tmux_sessions

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        try:
            sessions = await tmux_sessions.get()
        except Exception:
            sessions = []

        await ws.send_json(
            {
                "type": "init",
                "runs": orchestrator.get_all(),
                "sessions": sessions,
            }
        )
        await ws_hub.connect(ws)
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        await ws_hub.disconnect(ws)
