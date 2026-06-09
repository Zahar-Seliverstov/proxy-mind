from fastapi import APIRouter, HTTPException, Query, status
from services import fs

router = APIRouter(prefix="/fs", tags=["fs"])


@router.get("/browse", status_code=status.HTTP_200_OK)
async def browse(
    path: str | None = Query(None),
    kind: str = Query("dir", pattern="^(dir|file|all)$"),
):
    try:
        return fs.browse(path, kind)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
