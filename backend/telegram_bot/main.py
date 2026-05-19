import uvicorn
from fastapi import FastAPI
from router import router as send_router

app = FastAPI()
app.include_router(send_router)


@app.get("/")
def root():
    return {"message": "Telegram bot", "status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=3001, reload=True)
