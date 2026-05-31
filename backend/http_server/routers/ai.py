from fastapi import APIRouter, HTTPException, status
from loguru import logger
from schemas.ai_schema import (
    AnalyzeRequest,
    AnalyzeResponse,
    GenerateRequest,
    QuestionsRequest,
    RunRequest,
    ValidateRequest,
)
from services import ai, orchestrator

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/modes", status_code=status.HTTP_200_OK)
def get_modes():
    return {"modes": ai.list_modes()}


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate(body: ValidateRequest):
    try:
        return await ai.validate(body.prompt, body.mode, body.model)
    except Exception as e:
        logger.exception("validate failed — model={} mode={}", body.model, body.mode)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/questions", status_code=status.HTTP_200_OK)
async def questions(body: QuestionsRequest):
    try:
        history = [h.model_dump() for h in body.history]
        return await ai.get_next_question(body.prompt, body.mode, body.model, history)
    except Exception as e:
        logger.exception("questions failed — model={} history_len={}", body.model, len(body.history))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/generate", status_code=status.HTTP_200_OK)
async def generate(body: GenerateRequest):
    try:
        return await ai.generate(body.prompt, body.mode, body.model, body.answers)
    except Exception as e:
        logger.exception("generate failed — model={} mode={} answers={}", body.model, body.mode, body.answers)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run(body: RunRequest):
    try:
        prompts = await ai.translate_prompts(body.mode, body.model, body.content, body.steps)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    try:
        return await orchestrator.start(body.pane_id, prompts, body.model)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/analyze", status_code=status.HTTP_200_OK, response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest):
    try:
        return await ai.analyze(body.pane_text, body.current_step, body.remaining_steps, body.model)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/runs/{pane_id}", status_code=status.HTTP_200_OK)
async def run_status(pane_id: str):
    return orchestrator.get(pane_id)


@router.post("/runs/{pane_id}/stop", status_code=status.HTTP_200_OK)
async def run_stop(pane_id: str):
    try:
        return await orchestrator.stop(pane_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/runs/{pane_id}/pause", status_code=status.HTTP_200_OK)
async def run_pause(pane_id: str):
    try:
        return await orchestrator.pause(pane_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/runs/{pane_id}/unpause", status_code=status.HTTP_200_OK)
async def run_unpause(pane_id: str):
    try:
        return await orchestrator.unpause(pane_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
