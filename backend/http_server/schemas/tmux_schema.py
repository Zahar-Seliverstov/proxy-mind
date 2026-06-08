from typing import Annotated
from pydantic import BaseModel, BeforeValidator, field_validator

from schemas import NonEmptyStr


def _empty_str_to_none(v: str | None) -> str | None:
    if isinstance(v, str) and not v.strip():
        return None
    return v


OptionalStr = Annotated[str | None, BeforeValidator(_empty_str_to_none)]


class CreateSession(BaseModel):
    session_name: OptionalStr = None
    start_directory: OptionalStr = None


class AttachSession(BaseModel):
    terminal_name: NonEmptyStr
    window_id: OptionalStr = None
    pane_id: OptionalStr = None


class CreateWindow(BaseModel):
    session_name: str


class CreatePane(BaseModel):
    window_id: str
    vertical: bool = False
    start_directory: OptionalStr = None


class SendText(BaseModel):
    text: str
    enter: bool = True


_ALLOWED_KEYS = {
    "Enter",
    "Escape",
    "Tab",
    "BSpace",
    "Space",
    "Up",
    "Down",
    "Left",
    "Right",
    "C-c",
    "C-z",
    "C-d",
    "C-l",
}


class SendKey(BaseModel):
    key: str

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if v not in _ALLOWED_KEYS:
            raise ValueError(
                f"Недопустимая клавиша '{v}'. Доступные: {', '.join(sorted(_ALLOWED_KEYS))}"
            )
        return v
