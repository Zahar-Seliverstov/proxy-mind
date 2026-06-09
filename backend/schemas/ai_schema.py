from typing import Any
from enum import Enum
from pydantic import BaseModel, field_validator, model_validator

from schemas import NonEmptyStr


class Mode(str, Enum):
    plan = "plan"
    optimize = "optimize"
    direct = "direct"
    manual = "manual"


class QAItem(BaseModel):
    question: str
    answer: str


class ValidateRequest(BaseModel):
    prompt: NonEmptyStr
    mode: Mode
    model: NonEmptyStr


class QuestionsRequest(BaseModel):
    prompt: NonEmptyStr
    mode: Mode
    model: NonEmptyStr
    history: list[QAItem] = []


class GenerateRequest(BaseModel):
    prompt: NonEmptyStr
    mode: Mode
    model: NonEmptyStr
    answers: list[str] | None = None

    @field_validator("mode")
    @classmethod
    def not_direct(cls, v: Mode) -> Mode:
        if v in (Mode.direct, Mode.manual):
            raise ValueError(f"Режим '{v.value}' не требует генерации.")
        return v


class RunRequest(BaseModel):
    mode: Mode
    model: NonEmptyStr
    pane_id: NonEmptyStr
    content: str | None = None
    steps: list[str] | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "RunRequest":
        if self.mode in (Mode.plan, Mode.manual):
            if not self.steps:
                raise ValueError(
                    f"Для режима '{self.mode.value}' необходимо передать 'steps'."
                )
        else:
            if not self.content or not self.content.strip():
                raise ValueError(
                    "Для режимов 'optimize' и 'direct' необходимо передать 'content'."
                )
        return self


class AnalyzeRequest(BaseModel):
    pane_text: str
    current_step: NonEmptyStr
    remaining_steps: list[str] = []
    model: NonEmptyStr


class AnalyzeResponse(BaseModel):
    state: str
    reason: str
    payload: dict[str, Any] = {}
