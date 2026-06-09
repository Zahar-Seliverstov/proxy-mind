"""
Структурное тестирование модуля services/ai.py.

Проверяет функцию _combine — объединение редактируемого содержимого промпта
с его заблокированной частью формата.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.ai import _combine


class TestCombine:
    def test_with_format_hint_joins_with_double_newline(self):
        result = _combine("Do the task", "Return JSON only")
        assert result == "Do the task\n\nReturn JSON only"

    def test_without_format_hint_returns_content_only(self):
        result = _combine("Do the task", None)
        assert result == "Do the task"

    def test_empty_format_hint_string_is_treated_as_falsy(self):
        result = _combine("content", "")
        assert result == "content"

    def test_multiline_content_preserved(self):
        content = "Line one\nLine two\nLine three"
        hint = "Output: JSON"
        result = _combine(content, hint)
        assert result.startswith(content)
        assert result.endswith(hint)
        assert "\n\n" in result

    def test_format_hint_appended_after_separator(self):
        content = "Analyze the code"
        hint = 'Respond with {"status": "..."}'
        result = _combine(content, hint)
        parts = result.split("\n\n")
        assert parts[0] == content
        assert parts[1] == hint

    def test_empty_content_with_hint(self):
        result = _combine("", "format spec")
        assert result == "\n\nformat spec"

    def test_empty_content_no_hint(self):
        result = _combine("", None)
        assert result == ""
