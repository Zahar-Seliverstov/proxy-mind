from fastapi import APIRouter, status
from .sessions import router as sessions_router
from .windows import router as windows_router
from .panes import router as panes_router
from ._broadcast import broadcast_tree

router = APIRouter(prefix="/tmux", tags=["tmux"])
router.include_router(sessions_router)
router.include_router(windows_router)
router.include_router(panes_router)


@router.get("/hook", status_code=status.HTTP_204_NO_CONTENT)
async def tmux_hook():
    broadcast_tree()
