import libtmux
from libtmux.pane import PaneDirection

from ._helpers import find_pane, find_window


def _require_pane(pane_id: str):
    pane = find_pane(libtmux.Server(), pane_id)
    if pane is None:
        raise ValueError(f"Панель '{pane_id}' не найдена.")
    return pane


def _require_window(window_id: str):
    window = find_window(libtmux.Server(), window_id)
    if window is None:
        raise ValueError(f"Окно '{window_id}' не найдено.")
    return window


async def get_content(pane_id: str) -> list[str]:
    return _require_pane(pane_id).capture_pane()


async def send_text(pane_id: str, text: str, enter: bool) -> None:
    _require_pane(pane_id).send_keys(text, enter=enter)


async def send_key(pane_id: str, key: str) -> None:
    _require_pane(pane_id).send_keys(key, enter=False)


async def create(window_id: str, vertical: bool, start_directory: str | None = None) -> dict:
    direction = PaneDirection.Below if vertical else PaneDirection.Right
    pane = _require_window(window_id).split(direction=direction, start_directory=start_directory)
    return {
        "id": pane.pane_id,
        "command": pane.pane_current_command,
        "path": pane.pane_current_path,
        "pid": int(pane.pane_pid),
    }


async def remove(pane_id: str) -> None:
    _require_pane(pane_id).kill()
