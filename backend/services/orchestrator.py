import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from services import ai
from services import notifications
from services import tmux
from services import ws_hub

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b[()].")

POLL_INTERVAL_S = 0.3
STABLE_MS = 1500
INITIAL_GRACE_S = 1.0
MAX_STABLE_WAIT_S = 30.0
PANE_TAIL_LINES = 200
MAX_AUTO_REPLIES_PER_QUESTION = 5
ANALYZE_MAX_RETRIES = 3
MAX_ITERATIONS_PER_STEP = 60
MAX_EMPTY_OPEN_REPLIES = 3
TERMINAL_RETENTION_S = 300


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
    seq: int = 0
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Run:
    pane_id: str
    model: str
    prompts: list[str]
    status: str = "running"
    step_index: int = 0
    sent_current_step: bool = False
    last_decision: dict[str, Any] | None = None
    log: list[_DecisionLogEntry] = field(default_factory=list)
    error: str | None = None
    task: asyncio.Task | None = None
    empty_reply_count: int = 0
    _seq: int = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "pane_id": self.pane_id,
            "status": self.status,
            "step_index": self.step_index,
            "total_steps": len(self.prompts),
            "current_step": self.prompts[self.step_index]
            if self.step_index < len(self.prompts)
            else None,
            "steps": list(self.prompts),
            "last_decision": self.last_decision,
            "error": self.error,
            "log": [
                {
                    "at": e.at,
                    "step_index": e.step_index,
                    "state": e.state,
                    "reason": e.reason,
                    "seq": e.seq,
                    "payload": e.payload,
                }
                for e in self.log
            ],
        }


_runs: dict[str, _Run] = {}
_lock = asyncio.Lock()

_bg_tasks: set[asyncio.Task] = set()

_TERMINAL = ("done", "error", "stopped")
_PAUSED = ("user_paused", "limit_paused")


def _spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return task


async def _expire_terminal(pane_id: str) -> None:
    await asyncio.sleep(TERMINAL_RETENTION_S)
    async with _lock:
        run = _runs.get(pane_id)
        if run and run.status in _TERMINAL:
            _runs.pop(pane_id, None)


def _detect_limit(text: str) -> bool:
    pattern = ai.build_limit_regex()
    return pattern is not None and bool(pattern.search(text))


async def start(pane_id: str, prompts: list[str], model: str) -> dict[str, Any]:
    async with _lock:
        existing = _runs.get(pane_id)
        if existing and existing.status in ("running", *_PAUSED):
            raise RuntimeError(
                f"На панели '{pane_id}' уже идёт запуск (status={existing.status})."
            )
        run = _Run(pane_id=pane_id, model=model, prompts=list(prompts))
        _runs[pane_id] = run
        run.task = asyncio.create_task(_run_loop(run))
    snap = run.snapshot()
    await ws_hub.broadcast({"type": "run:status", "pane_id": pane_id, "snapshot": snap})
    return snap


def get(pane_id: str) -> dict[str, Any] | None:
    run = _runs.get(pane_id)
    return run.snapshot() if run else None


def get_all() -> dict[str, dict[str, Any]]:

    return {
        pid: run.snapshot()
        for pid, run in list(_runs.items())
        if run.status not in _TERMINAL
    }


async def stop(pane_id: str) -> dict[str, Any]:
    async with _lock:
        run = _runs.get(pane_id)
        if run is None:
            raise ValueError(f"На панели '{pane_id}' нет активного запуска.")
        if run.status in ("running", *_PAUSED):
            run.status = "stopped"
            if run.task and not run.task.done():
                run.task.cancel()
        snap = run.snapshot()
        if run.status in ("done", "error", "stopped"):
            _runs.pop(pane_id, None)
    await ws_hub.broadcast({"type": "run:status", "pane_id": pane_id, "snapshot": snap})
    return snap


async def pause(pane_id: str) -> dict[str, Any]:
    async with _lock:
        run = _runs.get(pane_id)
        if run is None:
            raise ValueError(f"На панели '{pane_id}' нет активного запуска.")
        if run.status != "running":
            raise ValueError(
                f"Поставить на паузу можно только running-запуск (текущее: {run.status})."
            )
        run.status = "user_paused"
        snap = run.snapshot()
    await ws_hub.broadcast({"type": "run:status", "pane_id": pane_id, "snapshot": snap})
    return snap


async def unpause(pane_id: str) -> dict[str, Any]:
    async with _lock:
        run = _runs.get(pane_id)
        if run is None:
            raise ValueError(f"На панели '{pane_id}' нет запуска.")
        if run.status != "user_paused":
            raise ValueError(
                f"Снять с паузы можно только user_paused-запуск (текущее: {run.status})."
            )
        run.status = "running"
        if run.task is None or run.task.done():
            run.task = asyncio.create_task(_run_loop(run))
        snap = run.snapshot()
    await ws_hub.broadcast({"type": "run:status", "pane_id": pane_id, "snapshot": snap})
    return snap


async def resume(pane_id: str) -> dict[str, Any]:
    """Возобновить запуск после limit_paused — повторно отправить текущий шаг."""
    async with _lock:
        run = _runs.get(pane_id)
        if run is None:
            raise ValueError(f"На панели '{pane_id}' нет запуска.")
        if run.status != "limit_paused":
            raise ValueError(
                f"Resume доступен только для limit_paused-запуска (текущее: {run.status})."
            )
        run.status = "running"
        run.sent_current_step = False
        if run.task is None or run.task.done():
            run.task = asyncio.create_task(_run_loop(run))
        snap = run.snapshot()
    await ws_hub.broadcast({"type": "run:status", "pane_id": pane_id, "snapshot": snap})
    return snap


async def _run_loop(run: _Run) -> None:
    try:
        while run.step_index < len(run.prompts):
            if run.status in ("stopped", "error", "done"):
                break
            if run.status in _PAUSED:
                await asyncio.sleep(POLL_INTERVAL_S)
                continue
            if not run.sent_current_step:
                await _send_current_step(run)
                run.sent_current_step = True
            await _drive_until_step_advances(run)
    except asyncio.CancelledError:
        logger.info("Запуск на pane={} отменён", run.pane_id)
        run.status = "stopped"
    except Exception as e:
        logger.exception("Сбой оркестратора на pane={}", run.pane_id)
        run.status = "error"
        run.error = str(e)
    else:
        if run.status == "running":
            run.status = "done"
    await ws_hub.broadcast(
        {"type": "run:status", "pane_id": run.pane_id, "snapshot": run.snapshot()}
    )
    if run.status in _TERMINAL:
        _spawn(_expire_terminal(run.pane_id))
    if run.status == "done":
        await notifications.notify(_notify_done(run))
    elif run.status == "error":
        await notifications.notify(_notify_error(run))
    elif run.status == "limit_paused":
        await notifications.notify(_notify_limit_paused(run))


def _notify_done(run: _Run) -> str:
    steps_preview = "\n".join(
        f"  {i + 1}. {s[:60]}{'…' if len(s) > 60 else ''}"
        for i, s in enumerate(run.prompts)
    )
    return (
        f"✅ <b>Задача выполнена</b>\n\n"
        f"<b>Панель:</b> <code>{run.pane_id}</code>\n"
        f"<b>Модель:</b> <code>{run.model}</code>\n"
        f"<b>Шагов выполнено:</b> {len(run.prompts)}\n\n"
        f"<b>Шаги:</b>\n{steps_preview}"
    )


def _notify_error(run: _Run) -> str:
    msg = (
        f"❌ <b>Ошибка выполнения</b>\n\n"
        f"<b>Панель:</b> <code>{run.pane_id}</code>\n"
        f"<b>Модель:</b> <code>{run.model}</code>\n"
        f"<b>Выполнено шагов:</b> {run.step_index} из {len(run.prompts)}"
    )
    if run.error:
        msg += f"\n\n<b>Причина:</b>\n<code>{run.error[:300]}</code>"
    return msg


def _notify_limit_paused(run: _Run) -> str:
    return (
        f"⏸ <b>Выполнение приостановлено — лимит CLI</b>\n\n"
        f"<b>Панель:</b> <code>{run.pane_id}</code>\n"
        f"<b>Модель:</b> <code>{run.model}</code>\n"
        f"<b>Выполнено шагов:</b> {run.step_index} из {len(run.prompts)}\n"
        f"<b>Текущий шаг:</b> {run.step_index + 1}\n\n"
        f"Пополните баланс или дождитесь сброса лимита, затем нажмите <b>Resume</b> в интерфейсе."
    )


async def _send_current_step(run: _Run) -> None:
    prompt = _sanitize_for_tui(run.prompts[run.step_index])
    await tmux.panes.send_text(run.pane_id, prompt, enter=True)


def _sanitize_for_tui(text: str) -> str:
    return " ".join(text.split()).strip()


async def _drive_until_step_advances(run: _Run) -> None:
    await asyncio.sleep(INITIAL_GRACE_S)
    last_question: str = ""
    repeat_count: int = 0
    iterations: int = 0
    while run.status == "running":
        await _wait_for_stable(run)
        if run.status != "running":
            return
        lines = await tmux.panes.get_content(run.pane_id)
        pane_text = _clean_pane(_tail(lines))
        if _detect_limit(pane_text):
            run.status = "limit_paused"
            await ws_hub.broadcast(
                {"type": "run:status", "pane_id": run.pane_id, "snapshot": run.snapshot()}
            )
            await notifications.notify(_notify_limit_paused(run))
            return
        decision = await _analyze(run)
        if run.status != "running":
            return
        _record(run, decision)

        if decision["state"] == "working":
            iterations = 0
        else:
            iterations += 1
            if iterations > MAX_ITERATIONS_PER_STEP:
                run.status = "error"
                run.error = (
                    f"Зависание: шаг #{run.step_index + 1} не завершился за "
                    f"{MAX_ITERATIONS_PER_STEP} непродуктивных итераций анализа."
                )
                return
        if decision["state"] == "ask_user":
            q = decision["payload"].get("question", "")
            if q == last_question:
                repeat_count += 1
                if repeat_count >= MAX_AUTO_REPLIES_PER_QUESTION:
                    run.status = "error"
                    run.error = f"Зависание: одинаковый вопрос получен {repeat_count} раз подряд: «{q[:120]}»"
                    return
            else:
                last_question = q
                repeat_count = 1
        else:
            last_question = ""
            repeat_count = 0
        if await _act(run, decision):
            return


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
            logger.warning(
                "pane={} стабилизация не дождалась, форсируем анализ", run.pane_id
            )
            return
        await asyncio.sleep(POLL_INTERVAL_S)


async def _analyze(run: _Run) -> dict[str, Any]:
    lines = await tmux.panes.get_content(run.pane_id)
    pane_text = _clean_pane(_tail(lines))
    current = run.prompts[run.step_index]
    remaining = run.prompts[run.step_index + 1 :]
    last_err: str = ""
    for attempt in range(ANALYZE_MAX_RETRIES):
        try:
            result = await ai.analyze(pane_text, current, remaining, run.model)
            if not ai.is_fallback(result):
                return result
            last_err = result["reason"]
            logger.warning(
                "analyze попытка {}/{}: {}", attempt + 1, ANALYZE_MAX_RETRIES, last_err
            )
        except Exception as e:
            last_err = str(e)
            logger.exception(
                "Ошибка analyze() на pane={} попытка {}", run.pane_id, attempt + 1
            )
        if attempt < ANALYZE_MAX_RETRIES - 1:
            await asyncio.sleep(1.0)
    return {
        "state": "ask_user",
        "reason": last_err or "сбой анализатора",
        "payload": {},
    }


def _record(run: _Run, decision: dict[str, Any]) -> None:
    run.last_decision = decision
    run._seq += 1
    entry = _DecisionLogEntry(
        at=time.time(),
        step_index=run.step_index,
        state=decision["state"],
        reason=decision["reason"],
        seq=run._seq,
        payload=decision["payload"],
    )
    run.log.append(entry)
    _spawn(
        ws_hub.broadcast(
            {
                "type": "run:event",
                "pane_id": run.pane_id,
                "entry": {
                    "at": entry.at,
                    "step_index": entry.step_index,
                    "state": entry.state,
                    "reason": entry.reason,
                    "seq": entry.seq,
                    "payload": entry.payload,
                },
                "step_index": run.step_index,
                "status": run.status,
            }
        )
    )


async def _act(run: _Run, decision: dict[str, Any]) -> bool:
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

    return await _auto_answer(run, decision)


async def _auto_answer(run: _Run, decision: dict[str, Any]) -> bool:
    payload = decision.get("payload") or {}
    lines = await tmux.panes.get_content(run.pane_id)
    pane_text = _clean_pane(_tail(lines))
    current = run.prompts[run.step_index] if run.step_index < len(run.prompts) else ""
    remaining = run.prompts[run.step_index + 1 :]
    try:
        text = await ai.decide_reply(pane_text, current, remaining, payload, run.model)
    except Exception:
        logger.exception("decide_reply упал на pane={}", run.pane_id)
        text = ""

    question = (payload.get("question") or "").strip()
    reply = _sanitize_for_tui(text)
    if not reply:
        run.empty_reply_count += 1
        logger.warning(
            "Пустой авто-ответ на pane={} ({}/{}), Enter не отправляем",
            run.pane_id,
            run.empty_reply_count,
            MAX_EMPTY_OPEN_REPLIES,
        )
        _record(
            run,
            {
                "state": "auto_reply",
                "reason": decision.get("reason", "пустой авто-ответ — пропущен"),
                "payload": {
                    "question": question,
                    "text": "",
                    "kind": payload.get("kind"),
                },
            },
        )
        if run.empty_reply_count >= MAX_EMPTY_OPEN_REPLIES:
            run.status = "error"
            run.error = (
                f"Зависание: анализатор {run.empty_reply_count} раз подряд не смог "
                f"сформировать ответ на вопрос CLI: «{question[:120]}»"
            )
            return True
        return False
    run.empty_reply_count = 0
    _record(
        run,
        {
            "state": "auto_reply",
            "reason": decision.get("reason", "автоматический ответ"),
            "payload": {
                "question": question,
                "text": reply,
                "kind": payload.get("kind"),
            },
        },
    )
    await tmux.panes.send_text(run.pane_id, reply, enter=True)
    return False
