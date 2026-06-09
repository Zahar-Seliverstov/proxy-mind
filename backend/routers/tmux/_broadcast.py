import asyncio
from services import ws_hub
from services.tmux import sessions as tmux_sessions

_bg_tasks: set[asyncio.Task] = set()


async def _do_broadcast() -> None:
    await asyncio.sleep(0.15)
    try:
        sessions = await tmux_sessions.get()
    except Exception:
        return
    await ws_hub.broadcast({"type": "tmux:tree", "sessions": sessions})


def broadcast_tree() -> None:
    task = asyncio.create_task(_do_broadcast())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
