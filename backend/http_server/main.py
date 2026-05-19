import libtmux.exc
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from routers.tmux import router as tmux_router
from routers.fs import router as fs_router
from routers.ollama import router as ollama_router
from routers.ai import router as ai_router
from routers.settings import router as settings_router

app = FastAPI()

app.include_router(tmux_router)
app.include_router(fs_router)
app.include_router(ollama_router)
app.include_router(ai_router)
app.include_router(settings_router)


@app.exception_handler(libtmux.exc.LibTmuxException)
async def libtmux_exception_handler(request: Request, exc: libtmux.exc.LibTmuxException):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка tmux. Проверьте, что tmux запущен и доступен."},
    )


@app.get("/")
def root():
    return {"message": "Hello World!", "status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=3000, reload=True)
