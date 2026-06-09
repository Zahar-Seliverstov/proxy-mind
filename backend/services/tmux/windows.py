import libtmux

from ._helpers import find_session, find_window


async def create(session_name: str) -> None:
    server = libtmux.Server()
    session = find_session(server, session_name)
    if session is None:
        raise ValueError(f"Сессия '{session_name}' не существует.")
    session.new_window(start_directory=session.session_path)


async def remove(window_id: str) -> None:
    window = find_window(libtmux.Server(), window_id)
    if window is None:
        raise ValueError(f"Окно '{window_id}' не существует.")
    window.kill()
