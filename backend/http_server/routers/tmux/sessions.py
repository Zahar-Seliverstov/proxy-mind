import libtmux.exc
from fastapi import APIRouter, HTTPException, status
from schemas import tmux_schema
from services import tmux
from ._broadcast import broadcast_tree

router = APIRouter(prefix="/sessions")


@router.get("", status_code=status.HTTP_200_OK)
async def get_sessions():
    sessions = await tmux.sessions.get()
    return {"sessions": sessions}


@router.get("/{session_name}", status_code=status.HTTP_200_OK)
async def get_session(session_name: str):
    try:
        session = await tmux.sessions.get_by_name(session_name)
        return {"session": session}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(schema: tmux_schema.CreateSession):
    try:
        created_name = await tmux.sessions.create(
            schema.session_name, schema.start_directory
        )
        broadcast_tree()
        return {
            "message": f"Сессия '{created_name}' успешно создана.",
            "session_name": created_name,
        }
    except libtmux.exc.TmuxSessionExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Сессия с именем '{schema.session_name}' уже существует.",
        )


@router.delete("/{session_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_session(session_name: str):
    try:
        await tmux.sessions.remove(session_name)
        broadcast_tree()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{session_name}/detach", status_code=status.HTTP_200_OK)
async def detach_session(session_name: str):
    try:
        await tmux.sessions.detach(session_name)
        broadcast_tree()
        return {"message": f"Сессия '{session_name}' успешно отключена."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{session_name}/attach", status_code=status.HTTP_200_OK)
async def attach_session(session_name: str, schema: tmux_schema.AttachSession):
    try:
        await tmux.sessions.attach(
            session_name, schema.terminal_name, schema.window_id, schema.pane_id
        )
        broadcast_tree()
        return {
            "message": f"Терминал '{schema.terminal_name}' успешно подключён к сессии '{session_name}'."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
