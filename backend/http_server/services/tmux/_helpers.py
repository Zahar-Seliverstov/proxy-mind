import libtmux


def find_session(server: libtmux.Server, session_name: str):
    return next((s for s in server.sessions if s.session_name == session_name), None)


def find_window(server: libtmux.Server, window_id: str):
    return next(
        (w for s in server.sessions for w in s.windows if w.window_id == window_id),
        None,
    )


def find_pane(server: libtmux.Server, pane_id: str):
    return next(
        (p for s in server.sessions for w in s.windows for p in w.panes if p.pane_id == pane_id),
        None,
    )
