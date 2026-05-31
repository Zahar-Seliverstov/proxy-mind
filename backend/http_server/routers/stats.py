import libtmux
from fastapi import APIRouter, status

router = APIRouter()


def _session_stats(s) -> dict:
    return {
        "id": s.session_id,
        "name": s.session_name,
        "attached": bool(int(s.session_attached)),
        "created": int(s.session_created),
        "path": s.session_path,
    }


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_stats():
    server = libtmux.Server()
    return {"sessions": [_session_stats(s) for s in server.sessions]}
