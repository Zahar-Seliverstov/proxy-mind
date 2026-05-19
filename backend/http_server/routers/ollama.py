from fastapi import APIRouter, HTTPException, status
from services import ollama

router = APIRouter(prefix="/ollama", tags=["ollama"])


@router.get("/models", status_code=status.HTTP_200_OK)
async def get_models():
    try:
        return {"models": await ollama.get_models()}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
