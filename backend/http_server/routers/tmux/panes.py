from fastapi import APIRouter, HTTPException, status
from schemas import tmux_schema
from services import tmux

router = APIRouter(prefix="/panes")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_pane(schema: tmux_schema.CreatePane):
    try:
        pane = await tmux.panes.create(schema.window_id, schema.vertical, schema.start_directory)
        return {"pane": pane}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{pane_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_pane(pane_id: str):
    try:
        await tmux.panes.remove(pane_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{pane_id}/content", status_code=status.HTTP_200_OK)
async def get_content(pane_id: str):
    try:
        content = await tmux.panes.get_content(pane_id)
        return {"content": content}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{pane_id}/send-text", status_code=status.HTTP_200_OK)
async def send_text(pane_id: str, schema: tmux_schema.SendText):
    try:
        await tmux.panes.send_text(pane_id, schema.text, schema.enter)
        return {"message": f"Текст успешно отправлен в панель '{pane_id}'."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{pane_id}/send-key", status_code=status.HTTP_200_OK)
async def send_key(pane_id: str, schema: tmux_schema.SendKey):
    try:
        await tmux.panes.send_key(pane_id, schema.key)
        return {"message": f"Клавиша '{schema.key}' успешно отправлена в панель '{pane_id}'."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
