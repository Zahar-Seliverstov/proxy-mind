import sys
from pathlib import Path

_HTTP_SERVER = Path(__file__).resolve().parent.parent / "http_server"
if str(_HTTP_SERVER) not in sys.path:
    sys.path.append(str(_HTTP_SERVER))

from clients.telegram.client import send_message  # noqa: E402

__all__ = ["send_message"]
