from fastapi import APIRouter, HTTPException, status
from schemas import tmux_schema
from services import tmux

router = APIRouter(prefix="/windows")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_window(schema: tmux_schema.CreateWindow):
    try:
        await tmux.windows.create(schema.session_name)
        return {"message": f"Окно успешно создано в сессии '{schema.session_name}'."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_window(window_id: str):
    try:
        await tmux.windows.remove(window_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
