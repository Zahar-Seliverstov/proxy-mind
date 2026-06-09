import libtmux
from loguru import logger

_HOOK_EVENTS = [
    "session-created",
    "session-closed",
    "window-linked",
    "window-unlinked",
    "pane-exited",
    "client-attached",
    "client-detached",
    "client-session-changed",
]

_HOOK_URL = "http://127.0.0.1:3000/tmux/hook"
_HOOK_CMD = f'run-shell -b "curl -s -o /dev/null --max-time 2 {_HOOK_URL}"'


def register() -> None:
    try:
        server = libtmux.Server()
        if not server.is_alive():
            return
        for event in _HOOK_EVENTS:
            server.cmd("set-hook", "-g", event, _HOOK_CMD)
        logger.info("tmux-хуки зарегистрированы ({} событий).", len(_HOOK_EVENTS))
    except Exception as e:
        logger.warning("Не удалось зарегистрировать tmux-хуки: {}", e)
