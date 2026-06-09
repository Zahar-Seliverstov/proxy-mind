"""
Структурное тестирование Pydantic-схем (schemas/).

Проверяет валидацию входных данных на границе API:
- NonEmptyStr     — аннотированный тип с обрезкой пробелов
- RunRequest      — валидатор режима и полезной нагрузки
- GenerateRequest — запрет режимов direct/manual
- ValidateRequest — обязательные поля
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from pydantic import ValidationError

from schemas import NonEmptyStr
from schemas.ai_schema import (
    GenerateRequest,
    Mode,
    RunRequest,
    ValidateRequest,
)


# ---------------------------------------------------------------------------
# NonEmptyStr
# ---------------------------------------------------------------------------

class TestNonEmptyStr:
    def test_valid_string_passes(self):
        from pydantic import BaseModel

        class M(BaseModel):
            v: NonEmptyStr

        assert M(v="hello").v == "hello"

    def test_strips_whitespace(self):
        from pydantic import BaseModel

        class M(BaseModel):
            v: NonEmptyStr

        assert M(v="  hi  ").v == "hi"

    def test_empty_string_raises(self):
        from pydantic import BaseModel, ValidationError

        class M(BaseModel):
            v: NonEmptyStr

        with pytest.raises(ValidationError):
            M(v="")

    def test_whitespace_only_raises(self):
        from pydantic import BaseModel, ValidationError

        class M(BaseModel):
            v: NonEmptyStr

        with pytest.raises(ValidationError):
            M(v="   ")


# ---------------------------------------------------------------------------
# ValidateRequest
# ---------------------------------------------------------------------------

class TestValidateRequest:
    def test_valid_request(self):
        req = ValidateRequest(prompt="Fix the bug", mode="plan", model="qwen2.5")
        assert req.prompt == "Fix the bug"
        assert req.mode == Mode.plan

    def test_missing_prompt_raises(self):
        with pytest.raises(ValidationError):
            ValidateRequest(mode="plan", model="qwen2.5")

    def test_invalid_mode_raises(self):
        with pytest.raises(ValidationError):
            ValidateRequest(prompt="task", mode="unknown", model="qwen2.5")

    def test_empty_model_raises(self):
        with pytest.raises(ValidationError):
            ValidateRequest(prompt="task", mode="plan", model="")


# ---------------------------------------------------------------------------
# GenerateRequest
# ---------------------------------------------------------------------------

class TestGenerateRequest:
    def test_plan_mode_allowed(self):
        req = GenerateRequest(prompt="Build API", mode="plan", model="qwen2.5")
        assert req.mode == Mode.plan

    def test_optimize_mode_allowed(self):
        req = GenerateRequest(prompt="Refactor", mode="optimize", model="qwen2.5")
        assert req.mode == Mode.optimize

    def test_direct_mode_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            GenerateRequest(prompt="task", mode="direct", model="qwen2.5")
        assert "direct" in str(exc_info.value)

    def test_manual_mode_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            GenerateRequest(prompt="task", mode="manual", model="qwen2.5")
        assert "manual" in str(exc_info.value)


# ---------------------------------------------------------------------------
# RunRequest
# ---------------------------------------------------------------------------

class TestRunRequest:
    def test_plan_mode_requires_steps(self):
        with pytest.raises(ValidationError):
            RunRequest(mode="plan", model="qwen2.5", pane_id="%1")

    def test_plan_mode_with_steps_passes(self):
        req = RunRequest(
            mode="plan", model="qwen2.5", pane_id="%1",
            steps=["step 1", "step 2"],
        )
        assert req.steps == ["step 1", "step 2"]

    def test_manual_mode_requires_steps(self):
        with pytest.raises(ValidationError):
            RunRequest(mode="manual", model="qwen2.5", pane_id="%1")

    def test_optimize_mode_requires_content(self):
        with pytest.raises(ValidationError):
            RunRequest(mode="optimize", model="qwen2.5", pane_id="%1")

    def test_optimize_mode_with_content_passes(self):
        req = RunRequest(
            mode="optimize", model="qwen2.5", pane_id="%1",
            content="Refactor this function",
        )
        assert req.content == "Refactor this function"

    def test_direct_mode_requires_content(self):
        with pytest.raises(ValidationError):
            RunRequest(mode="direct", model="qwen2.5", pane_id="%1")

    def test_empty_pane_id_raises(self):
        with pytest.raises(ValidationError):
            RunRequest(mode="plan", model="qwen2.5", pane_id="", steps=["s1"])
