"""Telegram HTTP client for the standalone bot service.

The implementation is shared with the API server: the canonical version lives
in ``http_server/clients/telegram``. This module re-exports it so there is a
single ``send_message`` to maintain. ``http_server`` is *appended* (not
inserted) to ``sys.path`` so this service's own ``config``/``main`` modules
still take precedence — only the ``clients`` package, which exists nowhere
else, is resolved there.
"""
import sys
from pathlib import Path

_HTTP_SERVER = Path(__file__).resolve().parent.parent / "http_server"
if str(_HTTP_SERVER) not in sys.path:
    sys.path.append(str(_HTTP_SERVER))

from clients.telegram.client import send_message  # noqa: E402

__all__ = ["send_message"]
