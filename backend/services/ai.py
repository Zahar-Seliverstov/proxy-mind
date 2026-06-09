import json
import re

from loguru import logger
from sqlalchemy import select

from clients.ollama import client as ollama_client
from database.db import SessionLocal
from database.models import Mode, Prompt

_GARBAGE_RE = re.compile(r"<\|im_|[一-鿿぀-ヿ가-힯]")

# ---------------------------------------------------------------------------
# In-memory кэш — заполняется из БД при старте через load_from_db()
# ---------------------------------------------------------------------------
MODES: dict[str, dict] = {}
_prompts: dict[str, str] = {}
# Отдельное хранение частей для API редактора: {name: {content, format_hint}}
_prompt_parts: dict[str, dict] = {}


async def load_from_db() -> None:
    """Загружает режимы и промпты из БД в кэш."""
    async with SessionLocal() as session:
        modes_rows = (await session.execute(select(Mode))).scalars().all()
        for m in modes_rows:
            entry: dict = {"label": m.label, "description": m.description}
            if m.prompt_id is not None:
                p = await session.get(Prompt, m.prompt_id)
                if p:
                    entry["system"] = _combine(p.content, p.format_hint)
            MODES[m.key] = entry

        prompts_rows = (await session.execute(select(Prompt))).scalars().all()
        for p in prompts_rows:
            _prompts[p.name] = _combine(p.content, p.format_hint)
            _prompt_parts[p.name] = {
                "content": p.content,
                "format_hint": p.format_hint,
            }


def _combine(content: str, format_hint: str | None) -> str:
    if format_hint:
        return content + "\n\n" + format_hint
    return content


# ---------------------------------------------------------------------------
# JSON-схемы для ответов модели
# ---------------------------------------------------------------------------

_VALIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["ok", "low_info", "off_topic", "gibberish"],
        }
    },
    "required": ["status"],
}

_PLAN_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "state": {"type": "string"},
            "task": {"type": "string"},
            "avoid": {"type": "string"},
            "check": {"type": "string"},
        },
        "required": ["state", "task", "avoid", "check"],
    },
}

_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "done": {"type": "boolean"},
        "text": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["done"],
}

_ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {
        "state": {
            "type": "string",
            "enum": ["working", "next_step", "done", "error", "ask_user"],
        },
        "reason": {"type": "string"},
        "payload": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "kind": {"type": "string", "enum": ["yesno", "choice", "open"]},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
    "required": ["state", "reason"],
}

_REPLY_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
}

_TRANSLATE_ARRAY_SCHEMA = {"type": "array", "items": {"type": "string"}}

_VALID_STATUSES = {"ok", "low_info", "off_topic", "gibberish"}
_VALID_ANALYZE_STATES = {"working", "next_step", "done", "error", "ask_user"}
_VALID_ASK_KINDS = {"yesno", "choice", "open"}


# ---------------------------------------------------------------------------
# Вспомогательные функции парсинга
# ---------------------------------------------------------------------------

def _extract_json(raw: str, opener: str, closer: str):
    s, e = raw.find(opener), raw.rfind(closer)
    if s == -1 or e == -1:
        return None
    try:
        return json.loads(raw[s : e + 1])
    except json.JSONDecodeError:
        return None


def _extract_obj(raw: str) -> dict | None:
    return _extract_json(raw, "{", "}")


def _extract_arr(raw: str) -> list | None:
    return _extract_json(raw, "[", "]")


# ---------------------------------------------------------------------------
# Публичные функции AI
# ---------------------------------------------------------------------------

async def decide_reply(
    pane_text: str,
    current_step: str,
    remaining_steps: list[str],
    ask: dict,
    model: str,
) -> str:
    lines = [
        f"Current plan step: {current_step}",
        f"Steps remaining after this one: {len(remaining_steps)}",
    ]
    if remaining_steps:
        lines.append("Remaining step texts:")
        lines.extend(f"{i}. {s}" for i, s in enumerate(remaining_steps, 1))
    lines += [
        "",
        "CLI question:",
        ask.get("question", ""),
        f"kind: {ask.get('kind', 'open')}",
    ]
    if ask.get("options"):
        lines.append("Options:")
        lines.extend(
            f'  - label="{o.get("label", "")}", value="{o.get("value", "")}"'
            for o in ask["options"]
        )
    lines += [
        "",
        "Terminal output (last lines):",
        "```",
        pane_text.strip() or "(pane is empty)",
        "```",
    ]
    messages = [
        {"role": "system", "content": _prompts["auto_reply"]},
        {"role": "user", "content": "\n".join(lines)},
    ]
    response = await ollama_client.chat(
        model,
        messages,
        options={"num_predict": 200, "temperature": 0},
        response_format=_REPLY_SCHEMA,
    )
    raw = response["message"]["content"].strip()
    kind = ask.get("kind", "open")
    parsed = _extract_obj(raw)
    if parsed:
        text = str(parsed.get("text", "")).strip()
        if text:
            if kind == "yesno":
                t = text.lower()
                if t in ("y", "yes", "да"):
                    return "y"
                if t in ("n", "no", "нет"):
                    return "n"
            elif kind == "choice":
                valid = {
                    str(o.get("value", "")).strip() for o in ask.get("options", [])
                }
                if text in valid:
                    return text
            elif not _GARBAGE_RE.search(text):
                return text
    if kind == "yesno":
        return "n"
    if kind == "choice" and ask.get("options"):
        return str(ask["options"][0].get("value") or "1")
    return ""


async def validate(prompt: str, mode: str, model: str) -> dict:
    messages = [
        {"role": "system", "content": _prompts["validate"]},
        {"role": "user", "content": prompt},
    ]
    response = await ollama_client.chat(
        model,
        messages,
        options={"num_predict": 32, "temperature": 0},
        response_format=_VALIDATE_SCHEMA,
    )
    parsed = _extract_obj(response["message"]["content"].strip())
    status = (parsed or {}).get("status")
    if status in _VALID_STATUSES:
        if status == "low_info" and mode != "plan":
            status = "ok"
        return {"status": status}

    logger.warning(
        "validate: модель вернула невалидный статус {!r}, fallback → ok", status
    )
    return {"status": "ok"}


async def analyze(
    pane_text: str,
    current_step: str,
    remaining_steps: list[str],
    model: str,
) -> dict:
    parts = [
        "Terminal output (last lines):",
        "```",
        pane_text.strip() or "(pane is empty)",
        "```",
        "",
        f"Current plan step: {current_step}",
        f"Steps remaining after this one: {len(remaining_steps)}",
    ]
    if remaining_steps:
        parts.append("Remaining step texts:")
        for i, s in enumerate(remaining_steps, 1):
            parts.append(f"{i}. {s}")
    messages = [
        {"role": "system", "content": _prompts["analyze"]},
        {"role": "user", "content": "\n".join(parts)},
    ]
    response = await ollama_client.chat(
        model,
        messages,
        options={"num_predict": 256, "temperature": 0},
        response_format=_ANALYZE_SCHEMA,
    )
    return _parse_analyze(response["message"]["content"])


def _parse_analyze(raw: str) -> dict:
    parsed = _extract_obj(raw.strip())
    if parsed is None:
        return _ask_fallback("анализатор вернул не-JSON")

    state = parsed.get("state")
    if state not in _VALID_ANALYZE_STATES:
        return _ask_fallback(f"анализатор вернул неизвестное состояние '{state}'")

    reason = str(parsed.get("reason", "")).strip() or "без обоснования"
    payload = parsed.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    payload = _normalize_ask_payload(payload) if state == "ask_user" else {}
    return {"state": state, "reason": reason, "payload": payload}


def is_fallback(result: dict) -> bool:
    return bool(result.get("_fallback"))


def _ask_fallback(reason: str) -> dict:
    return {
        "state": "ask_user",
        "reason": reason,
        "_fallback": True,
        "payload": {
            "question": "Анализатор не смог понять состояние терминала. Что отправить в pane?",
            "kind": "open",
            "options": [],
        },
    }


def _normalize_ask_payload(payload: dict) -> dict:
    question = (
        str(payload.get("question") or "").strip() or "CLI ждёт ввода — что отправить?"
    )
    kind = payload.get("kind") if payload.get("kind") in _VALID_ASK_KINDS else "open"
    raw_options = payload.get("options") or []
    options: list[dict] = []
    if isinstance(raw_options, list):
        for opt in raw_options:
            if not isinstance(opt, dict):
                continue
            label = str(opt.get("label") or "").strip()
            value = str(opt.get("value") or "").strip()
            if not label and not value:
                continue
            options.append({"label": label or value, "value": value or label})
    if kind == "open":
        options = []
    return {
        "question": question,
        "kind": kind,
        "options": options,
    }


async def get_next_question(
    prompt: str, mode: str, model: str, history: list[dict]
) -> dict:
    mode_hint = MODES.get(mode, {}).get("description", "")
    lines = []
    if mode_hint:
        lines.append(f"Generation mode: {mode_hint}")
    lines.append(f"Original request: {prompt}")
    if history:
        lines.append(f"\nClarification history ({len(history)}):")
        for item in history:
            answer = (item.get("answer") or "").strip()
            lines.append(f"Q: {item['question']}")
            if answer:
                lines.append(f"A: {answer}")
            else:
                lines.append(
                    "A: [SKIPPED — user chose not to answer, do not ask this again]"
                )
    else:
        lines.append(
            "\n[No clarification history yet. If the request is already specific enough, "
            "return {\"done\": true} immediately. Only ask if something is genuinely unclear.]"
        )
    messages = [
        {"role": "system", "content": _prompts["next_question"]},
        {"role": "user", "content": "\n".join(lines)},
    ]
    response = await ollama_client.chat(
        model,
        messages,
        options={"num_predict": 256, "temperature": 0},
        response_format=_QUESTION_SCHEMA,
    )
    return {"question": _parse_single_question(response["message"]["content"])}


async def generate(
    prompt: str, mode: str, model: str, answers: list[str] | None = None
) -> dict:
    system = MODES[mode]["system"]
    user_content = prompt
    if answers:
        user_content = f"{prompt}\n\nAdditional clarifications:\n" + "\n".join(
            f"- {a}" for a in answers
        )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    if mode == "plan":
        response = await ollama_client.chat(
            model,
            messages,
            options={"temperature": 0.3},
            response_format=_PLAN_SCHEMA,
        )
        return {"mode": "plan", "steps": _parse_plan(response["message"]["content"])}

    response = await ollama_client.chat(model, messages, options={"temperature": 0.2})
    return {"mode": mode, "result": response["message"]["content"].strip()}


async def translate_prompts(
    mode: str,
    model: str,
    content: str | None,
    steps: list[str] | None,
) -> list[str]:
    if mode in ("plan", "manual"):
        return await _translate_array(steps or [], model)
    return [await _translate(content or "", model)]


def list_modes() -> list[dict]:
    return [
        {"key": k, "label": v["label"], "description": v["description"]}
        for k, v in MODES.items()
    ]


def list_prompts() -> list[dict]:
    return [
        {"name": k, "content": v["content"], "format_hint": v["format_hint"]}
        for k, v in _prompt_parts.items()
    ]


async def update_prompt(name: str, content: str) -> bool:
    if name not in _prompt_parts:
        return False
    async with SessionLocal() as session:
        row = (
            await session.execute(select(Prompt).where(Prompt.name == name))
        ).scalar_one_or_none()
        if row is None:
            return False
        row.content = content
        await session.commit()
    _prompt_parts[name]["content"] = content
    _prompts[name] = _combine(content, _prompt_parts[name]["format_hint"])
    return True


def build_limit_regex() -> re.Pattern | None:
    raw = _prompts.get("limit_patterns", "")
    patterns = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not patterns:
        return None
    combined = "|".join(f"(?:{p})" for p in patterns)
    try:
        return re.compile(combined, re.IGNORECASE)
    except re.error as exc:
        logger.warning("limit_patterns: ошибка компиляции regex — {}", exc)
        return None


async def _translate(text: str, model: str) -> str:
    messages = [
        {"role": "system", "content": _prompts["translate"]},
        {"role": "user", "content": text},
    ]
    response = await ollama_client.chat(model, messages, options={"temperature": 0})
    return response["message"]["content"].strip()


async def _translate_array(items: list[str], model: str) -> list[str]:
    if not items:
        return []
    messages = [
        {"role": "system", "content": _prompts["translate_array"]},
        {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
    ]
    response = await ollama_client.chat(
        model,
        messages,
        options={"temperature": 0},
        response_format=_TRANSLATE_ARRAY_SCHEMA,
    )
    raw = response["message"]["content"]
    parsed = _parse_strict_json_array(raw)
    if parsed is not None and len(parsed) == len(items):
        return parsed
    return [await _translate(item, model) for item in items]


def _parse_strict_json_array(raw: str) -> list[str] | None:
    parsed = _extract_arr(raw.strip())
    if not isinstance(parsed, list):
        return None
    if not all(isinstance(i, str) for i in parsed):
        return None
    return [s.strip() for s in parsed if s.strip()]


def _parse_single_question(raw: str) -> dict | None:
    raw = raw.strip()
    if not raw or raw.lower() == "null":
        return None
    parsed = _extract_obj(raw)
    if not parsed:
        return None
    if parsed.get("done") is True:
        return None
    text = str(parsed.get("text", "")).strip()
    options = [str(o).strip() for o in (parsed.get("options") or []) if str(o).strip()]
    if text and options:
        if _GARBAGE_RE.search(text) or any(_GARBAGE_RE.search(o) for o in options):
            return None
        return {"text": text, "options": options}
    return None


_PLAN_TEMPLATE = (
    "Состояние: {state}. Задача: {task}. Не делать: {avoid}. Проверка: {check}."
)


def _parse_plan(raw: str) -> list[str]:
    arr = _extract_arr(raw.strip())
    if arr is None:
        arr = [
            line.strip().lstrip("0123456789.-) ")
            for line in raw.splitlines()
            if line.strip()
        ]
    return _assemble_plan(arr)


def _assemble_plan(items: list) -> list[str]:
    steps: list[str] = []
    for it in items:
        if isinstance(it, dict):
            task = str(it.get("task", "")).strip()
            if not task:
                continue
            steps.append(
                _PLAN_TEMPLATE.format(
                    state=str(it.get("state", "")).strip() or "—",
                    task=task,
                    avoid=str(it.get("avoid", "")).strip() or "—",
                    check=str(it.get("check", "")).strip() or "—",
                )
            )
        elif isinstance(it, str) and it.strip():
            steps.append(it.strip())
    return steps
