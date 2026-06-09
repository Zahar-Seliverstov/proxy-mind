"""
Структурное тестирование модуля services/orchestrator.py.

Проверяет вспомогательные функции обработки текста терминала:
- _clean_pane  — удаление ANSI-escape-последовательностей и управляющих символов
- _sanitize_for_tui — нормализация текста перед отправкой в tmux
- _tail        — получение последних N строк вывода панели
- _hash_lines  — детерминированное хеширование состояния терминала
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.orchestrator import _clean_pane, _sanitize_for_tui, _tail, _hash_lines


# ---------------------------------------------------------------------------
# _clean_pane
# ---------------------------------------------------------------------------

class TestCleanPane:
    def test_removes_csi_color_sequence(self):
        raw = "\x1b[32mHello\x1b[0m"
        assert _clean_pane(raw) == "Hello"

    def test_removes_csi_cursor_movement(self):
        raw = "\x1b[2J\x1b[H text"
        assert _clean_pane(raw) == " text"

    def test_removes_ansi_charset_sequence(self):
        raw = "\x1b(Btext"
        assert _clean_pane(raw) == "text"

    def test_removes_control_characters(self):
        raw = "ab\x00\x01\x07\x1fcd"
        assert _clean_pane(raw) == "abcd"

    def test_preserves_newlines(self):
        raw = "line1\nline2\nline3"
        assert _clean_pane(raw) == "line1\nline2\nline3"

    def test_preserves_tabs(self):
        raw = "col1\tcol2"
        assert _clean_pane(raw) == "col1\tcol2"

    def test_empty_string(self):
        assert _clean_pane("") == ""

    def test_plain_text_unchanged(self):
        raw = "No special chars here 123"
        assert _clean_pane(raw) == raw

    def test_mixed_content(self):
        raw = "\x1b[1mBold\x1b[0m normal \x1b[31mred\x1b[0m"
        assert _clean_pane(raw) == "Bold normal red"

    def test_removes_bell_character(self):
        raw = "alert\x07done"
        assert _clean_pane(raw) == "alertdone"


# ---------------------------------------------------------------------------
# _sanitize_for_tui
# ---------------------------------------------------------------------------

class TestSanitizeForTui:
    def test_collapses_internal_newlines(self):
        text = "step one\nstep two\nstep three"
        assert _sanitize_for_tui(text) == "step one step two step three"

    def test_collapses_multiple_spaces(self):
        text = "word1   word2    word3"
        assert _sanitize_for_tui(text) == "word1 word2 word3"

    def test_strips_leading_trailing_whitespace(self):
        text = "   hello world   "
        assert _sanitize_for_tui(text) == "hello world"

    def test_collapses_tabs(self):
        text = "col1\tcol2\tcol3"
        assert _sanitize_for_tui(text) == "col1 col2 col3"

    def test_single_word_unchanged(self):
        assert _sanitize_for_tui("hello") == "hello"

    def test_empty_string(self):
        assert _sanitize_for_tui("") == ""

    def test_only_whitespace(self):
        assert _sanitize_for_tui("   \n\t  ") == ""

    def test_multiline_prompt_becomes_single_line(self):
        text = "Create a Flask app\nthat handles /health\nand /metrics endpoints"
        result = _sanitize_for_tui(text)
        assert "\n" not in result
        assert result == "Create a Flask app that handles /health and /metrics endpoints"


# ---------------------------------------------------------------------------
# _tail
# ---------------------------------------------------------------------------

class TestTail:
    def test_returns_last_n_lines(self):
        lines = [str(i) for i in range(10)]
        result = _tail(lines, n=3)
        assert result == "7\n8\n9"

    def test_returns_all_when_fewer_than_n(self):
        lines = ["a", "b", "c"]
        result = _tail(lines, n=10)
        assert result == "a\nb\nc"

    def test_single_line(self):
        assert _tail(["only"], n=5) == "only"

    def test_empty_list(self):
        assert _tail([], n=10) == ""

    def test_exact_n_lines(self):
        lines = ["x", "y", "z"]
        assert _tail(lines, n=3) == "x\ny\nz"


# ---------------------------------------------------------------------------
# _hash_lines
# ---------------------------------------------------------------------------

class TestHashLines:
    def test_same_input_produces_same_hash(self):
        lines = ["line1", "line2", "line3"]
        assert _hash_lines(lines) == _hash_lines(lines)

    def test_different_input_produces_different_hash(self):
        assert _hash_lines(["a", "b"]) != _hash_lines(["a", "c"])

    def test_order_matters(self):
        assert _hash_lines(["a", "b"]) != _hash_lines(["b", "a"])

    def test_empty_list(self):
        h = _hash_lines([])
        assert isinstance(h, str) and len(h) == 64

    def test_returns_sha256_hex(self):
        h = _hash_lines(["test"])
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
