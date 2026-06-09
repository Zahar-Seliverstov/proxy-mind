from typing import Annotated

from pydantic import AfterValidator


def _strip_not_empty(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Поле не может быть пустым.")
    return v


NonEmptyStr = Annotated[str, AfterValidator(_strip_not_empty)]
