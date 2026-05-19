"""Per-pane оркестратор: гонит цикл send → ждать стабилизации → analyze → act.

In-memory реестр. На каждую панель — максимум один активный запуск.
"""
import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from services import ai
from services import tmux

logger = logging.getLogger(__name__)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b[()].")

POLL_INTERVAL_S              = 0.3   # как часто читаем pane
STABLE_MS                    = 1500  # сколько хэш должен не меняться чтобы признать «стабилизировался»
INITIAL_GRACE_S              = 1.0   # подождать после send_text прежде чем начинать ловить стабилизацию
MAX_STABLE_WAIT_S            = 30.0  # верхний предел ожидания стабилизации
PANE_TAIL_LINES              = 200   # сколько последних строк pane передаём анализатору
MAX_AUTO_REPLIES_PER_QUESTION = 5    # одинаковый вопрос N раз подряд → считаем зависанием
ANALYZE_MAX_RETRIES          = 3     # сколько раз повторять analyze при битом JSON


def _hash_lines(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _tail(lines: list[str], n: int = PANE_TAIL_LINES) -> str:
    return "\n".join(lines[-n:])


def _clean_pane(text: str) -> str:
    text = _ANSI_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


@dataclass
class _DecisionLogEntry:
    at: float
    step_index: int
    state: str
    reason: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Run:
    pane_id: str
    model: str
    prompts: list[str]
    status: str = "running"   # running | user_paused | done | error | stopped
    step_index: int = 0
    sent_current_step: bool = False
    last_decision: dict[str, Any] | None = None
    log: list[_DecisionLogEntry] = field(default_factory=list)
    error: str | None = None
    task: asyncio.Task | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "pane_id": self.pane_id,
            "status": self.status,
            "step_index": self.step_index,
            "total_steps": len(self.prompts),
            "current_step": self.prompts[self.step_index] if self.step_index < len(self.prompts) else None,
            "steps": list(self.prompts),
            "last_decision": self.last_decision,
            "error": self.error,
            "log": [
                {
                    "at": e.at,
                    "step_index": e.step_index,
                    "state": e.state,
                    "reason": e.reason,
                    "payload": e.payload,
                }
                for e in self.log
            ],
        }


_runs: dict[str, _Run] = {}
_lock = asyncio.Lock()


async def start(pane_id: str, prompts: list[str], model: str) -> dict[str, Any]:
    async with _lock:
        existing = _runs.get(pane_id)
        if existing and existing.status in ("running", "user_paused"):
            raise RuntimeError(f"На панели '{pane_id}' уже идёт запуск (status={existing.status}).")
        run = _Run(pane_id=pane_id, model=model, prompts=list(prompts))
        _runs[pane_id] = run
        run.task = asyncio.create_task(_run_loop(run))
    return run.snapshot()


def get(pane_id: str) -> dict[str, Any] | None:
    run = _runs.get(pane_id)
    return run.snapshot() if run else None


async def stop(pane_id: str) -> dict[str, Any]:
    run = _runs.get(pane_id)
    if run is None:
        raise ValueError(f"На панели '{pane_id}' нет активного запуска.")
    if run.status in ("running", "user_paused"):
        run.status = "stopped"
        if run.task and not run.task.done():
            run.task.cancel()
    snap = run.snapshot()
    if run.status in ("done", "error", "stopped"):
        _runs.pop(pane_id, None)
    return snap


async def pause(pane_id: str) -> dict[str, Any]:
    run = _runs.get(pane_id)
    if run is None:
        raise ValueError(f"На панели '{pane_id}' нет активного запуска.")
    if run.status != "running":
        raise ValueError(f"Поставить на паузу можно только running-запуск (текущее: {run.status}).")
    run.status = "user_paused"
    return run.snapshot()


async def unpause(pane_id: str) -> dict[str, Any]:
    run = _runs.get(pane_id)
    if run is None:
        raise ValueError(f"На панели '{pane_id}' нет запуска.")
    if run.status != "user_paused":
        raise ValueError(f"Снять с паузы можно только user_paused-запуск (текущее: {run.status}).")
    run.status = "running"
    if run.task is None or run.task.done():
        run.task = asyncio.create_task(_run_loop(run))
    return run.snapshot()


async def _run_loop(run: _Run) -> None:
    try:
        while run.step_index < len(run.prompts) and run.status == "running":
            if not run.sent_current_step:
                await _send_current_step(run)
                run.sent_current_step = True
            await _drive_until_step_advances(run)
    except asyncio.CancelledError:
        logger.info("Запуск на pane=%s отменён", run.pane_id)
        run.status = "stopped"
    except Exception as e:
        logger.exception("Сбой оркестратора на pane=%s", run.pane_id)
        run.status = "error"
        run.error = str(e)
    else:
        if run.status == "running":
            run.status = "done"


async def _send_current_step(run: _Run) -> None:
    prompt = _sanitize_for_tui(run.prompts[run.step_index])
    await tmux.panes.send_text(run.pane_id, prompt, enter=True)


def _sanitize_for_tui(text: str) -> str:
    """Внутренние переводы строк превращают в пробелы — иначе libtmux пошлёт Enter
    на первом же \\n и CLI отправит обрубок раньше времени."""
    return " ".join(text.split()).strip()


async def _drive_until_step_advances(run: _Run) -> None:
    """Крутит стабилизацию + анализ + действие пока текущий шаг не сменится или мы не выйдем."""
    await asyncio.sleep(INITIAL_GRACE_S)
    last_question: str = ""
    repeat_count: int = 0
    while run.status == "running":
        await _wait_for_stable(run)
        if run.status != "running":
            return
        decision = await _analyze(run)
        if run.status != "running":
            return
        _record(run, decision)
        if decision["state"] == "ask_user":
            q = decision["payload"].get("question", "")
            if q and q == last_question:
                repeat_count += 1
                if repeat_count >= MAX_AUTO_REPLIES_PER_QUESTION:
                    run.status = "error"
                    run.error = (
                        f"Зависание: одинаковый вопрос получен {repeat_count} раз подряд: «{q[:120]}»"
                    )
                    return
            else:
                last_question = q
                repeat_count = 1
        else:
            last_question = ""
            repeat_count = 0
        if await _act(run, decision):
            return  # шаг сменился (next_step/done) или мы вышли (error/stopped)


async def _wait_for_stable(run: _Run) -> None:
    last_hash = None
    last_change = time.monotonic()
    started = time.monotonic()
    while run.status == "running":
        lines = await tmux.panes.get_content(run.pane_id)
        h = _hash_lines(lines)
        now = time.monotonic()
        if h != last_hash:
            last_hash = h
            last_change = now
        elif (now - last_change) * 1000 >= STABLE_MS:
            return
        if now - started > MAX_STABLE_WAIT_S:
            logger.warning("pane=%s стабилизация не дождалась, форсируем анализ", run.pane_id)
            return
        await asyncio.sleep(POLL_INTERVAL_S)


async def _analyze(run: _Run) -> dict[str, Any]:
    lines = await tmux.panes.get_content(run.pane_id)
    pane_text = _clean_pane(_tail(lines))
    current = run.prompts[run.step_index]
    remaining = run.prompts[run.step_index + 1:]
    last_err: str = ""
    for attempt in range(ANALYZE_MAX_RETRIES):
        try:
            result = await ai.analyze(pane_text, current, remaining, run.model)
            if result["state"] != "ask_user" or "анализатор" not in result["reason"]:
                return result
            last_err = result["reason"]
            logger.warning("analyze попытка %d/%d: %s", attempt + 1, ANALYZE_MAX_RETRIES, last_err)
        except Exception as e:
            last_err = str(e)
            logger.exception("Ошибка analyze() на pane=%s попытка %d", run.pane_id, attempt + 1)
        if attempt < ANALYZE_MAX_RETRIES - 1:
            await asyncio.sleep(1.0)
    return {"state": "ask_user", "reason": last_err or "сбой анализатора", "payload": {}}


def _record(run: _Run, decision: dict[str, Any]) -> None:
    run.last_decision = decision
    run.log.append(
        _DecisionLogEntry(
            at=time.time(),
            step_index=run.step_index,
            state=decision["state"],
            reason=decision["reason"],
            payload=decision["payload"],
        )
    )


async def _act(run: _Run, decision: dict[str, Any]) -> bool:
    """Возвращает True если шаг сменился или цикл должен прерваться."""
    state = decision["state"]

    if state == "working":
        return False

    if state == "next_step":
        run.step_index += 1
        run.sent_current_step = False
        if run.step_index >= len(run.prompts):
            run.status = "done"
        return True

    if state == "done":
        run.step_index = len(run.prompts)
        run.status = "done"
        return True

    if state == "error":
        run.status = "error"
        run.error = decision["reason"]
        return True

    # ask_user — AI всегда отвечает сам
    return await _auto_answer(run, decision)


async def _auto_answer(run: _Run, decision: dict[str, Any]) -> bool:
    payload = decision.get("payload") or {}
    lines = await tmux.panes.get_content(run.pane_id)
    pane_text = _tail(lines)
    current = run.prompts[run.step_index] if run.step_index < len(run.prompts) else ""
    remaining = run.prompts[run.step_index + 1:]
    try:
        text = await ai.decide_reply(pane_text, current, remaining, payload, run.model)
    except Exception:
        logger.exception("decide_reply упал на pane=%s", run.pane_id)
        text = ""

    question = (payload.get("question") or "").strip()
    _record(run, {
        "state": "auto_reply",
        "reason": decision.get("reason", "автоматический ответ"),
        "payload": {
            "question": question,
            "text": text,
            "kind": payload.get("kind"),
        },
    })
    await tmux.panes.send_text(run.pane_id, _sanitize_for_tui(text), enter=True)
    return False  # тот же шаг, ждём стабилизации
