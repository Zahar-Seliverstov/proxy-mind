from fastapi import APIRouter
from .sessions import router as sessions_router
from .windows import router as windows_router
from .panes import router as panes_router

router = APIRouter(prefix="/tmux", tags=["tmux"])
router.include_router(sessions_router)
router.include_router(windows_router)
router.include_router(panes_router)
