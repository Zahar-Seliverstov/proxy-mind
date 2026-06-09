import shutil
import subprocess

import libtmux
import libtmux.exc
from loguru import logger

from . import hooks
from ._helpers import find_session


def _serialize_session(s) -> dict:
    return {
        "id": s.session_id,
        "name": s.session_name,
        "attached": bool(int(s.session_attached)),
        "created": int(s.session_created),
        "path": s.session_path,
        "windows": [
            {
                "id": w.window_id,
                "name": w.window_name,
                "panes": [
                    {
                        "id": p.pane_id,
                        "command": p.pane_current_command,
                        "path": p.pane_current_path,
                        "pid": int(p.pane_pid),
                    }
                    for p in w.panes
                ],
            }
            for w in s.windows
        ],
    }


async def get() -> list[dict]:
    server = libtmux.Server()
    return [_serialize_session(s) for s in server.sessions]


async def get_by_name(session_name: str) -> dict:
    session = find_session(libtmux.Server(), session_name)
    if session is None:
        raise ValueError(f"Сессия '{session_name}' не существует.")
    return _serialize_session(session)


def _generate_unique_name(server: libtmux.Server) -> str:
    existing = {s.session_name for s in server.sessions}
    i = 1
    while f"session-{i}" in existing:
        i += 1
    return f"session-{i}"


async def create(name: str | None = None, start_directory: str | None = None) -> str:
    server = libtmux.Server()
    resolved_name = name or _generate_unique_name(server)
    try:
        server.new_session(session_name=resolved_name, start_directory=start_directory)
    except libtmux.exc.TmuxSessionExists:
        logger.warning("Сессия '{}' уже существует.", resolved_name)
        raise
    logger.info("Сессия '{}' создана.", resolved_name)
    hooks.register()
    return resolved_name


async def remove(session_name: str) -> None:
    session = find_session(libtmux.Server(), session_name)
    if session is None:
        raise ValueError(f"Сессия '{session_name}' не существует.")
    session.kill()


async def detach(session_name: str) -> None:
    session = find_session(libtmux.Server(), session_name)
    if session is None:
        raise ValueError(f"Сессия '{session_name}' не существует.")
    if not bool(int(session.session_attached)):
        raise ValueError(f"Сессия '{session_name}' не имеет подключённых клиентов.")
    session.detach_client()


async def attach(
    session_name: str,
    terminal_name: str,
    window_id: str | None = None,
    pane_id: str | None = None,
) -> None:
    session = find_session(libtmux.Server(), session_name)
    if session is None:
        raise ValueError(f"Сессия '{session_name}' не существует.")

    if not shutil.which(terminal_name):
        raise FileNotFoundError(f"Эмулятор терминала '{terminal_name}' не установлен.")

    target = session_name
    if window_id:
        target += f":{window_id}"
    if pane_id:
        target += f".{pane_id}"

    try:
        logger.info("Запуск терминала '{}' для цели '{}'.", terminal_name, target)
        subprocess.Popen(
            [terminal_name, "-e", "tmux", "attach-session", "-t", target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        logger.exception("Ошибка запуска процесса терминала.")
        raise RuntimeError("Не удалось запустить процесс терминала.")
