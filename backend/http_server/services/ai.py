import json
import re

from loguru import logger

from clients.ollama import client as ollama_client

_GARBAGE_RE = re.compile(r"<\|im_|[一-鿿぀-ヿ가-힯]")


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

MODES = {
    "plan": {
        "label": "Auto Plan",
        "description": "AI breaks your task into small verifiable steps and runs them one by one",
        "system": (
            "You split a user's request into an ordered chain of prompts for an AI "
            "coding assistant. Each prompt drives ONE small, separately verifiable "
            "iteration.\n\n"
            "── WHY THIS MATTERS ─────────────────────────────────────────────────\n"
            "An AI coding assistant builds everything mentioned in a prompt PLUS "
            "whatever 'seems logical to add'. If one prompt says 'make a bot with a "
            "schedule', it builds it all at once with no checkpoints; errors pile up "
            "and tangle together.\n"
            "Fix: each step = exactly ONE capability + an explicit ban on everything "
            "else.\n\n"
            "── OUTPUT: ARRAY OF STEP OBJECTS ────────────────────────────────────\n"
            "Each object has four fields, every value written in RUSSIAN:\n"
            "  state — what already works after the previous step "
            "(first step: 'ничего нет').\n"
            "  task  — the single capability to add now, and how it must behave.\n"
            "  avoid — what belongs to later steps and must NOT be touched now.\n"
            "  check — one concrete action that proves this capability works.\n\n"
            "── RESPONSIBILITY BOUNDARY ──────────────────────────────────────────\n"
            "Describe WHAT is needed and HOW IT MUST BEHAVE.\n"
            "Do NOT specify libraries, file/function/class names, or architecture.\n"
            "Use only the technologies and names the user named themselves. "
            "Invent nothing.\n\n"
            "── STEP COUNT ───────────────────────────────────────────────────────\n"
            "Usually 3-8. Too large = several capabilities in one step. "
            "Too small = can't be checked on its own.\n\n"
            "── KEEP EVERY DETAIL ────────────────────────────────────────────────\n"
            "Every detail the user gave, and every clarification answer, must appear "
            "in some step — lose nothing. If the user said 'in Python', write Python; "
            "if 'use Redis', write Redis. Add nothing they did not say.\n\n"
            "── GOOD EXAMPLE (request: 'Telegram bot that sends a schedule') ──────\n"
            "[\n"
            '  {"state":"ничего нет",'
            '"task":"создать Telegram-бота, который на команду /start отвечает '
            "строкой 'бот работает'\","
            '"avoid":"другие команды, хранилище, меню, обработка любых других '
            'сообщений","check":"написать боту /start — приходит ответ '
            "'бот работает'\"},\n"
            '  {"state":"бот отвечает на /start строкой \'бот работает\'",'
            '"task":"добавить команду /schedule, возвращающую три захардкоженные '
            "строки расписания через разделитель ' | '\","
            '"avoid":"чтение из файла, разбиение по дням, сохранение состояния",'
            '"check":"/schedule возвращает эти три строки"},\n'
            '  {"state":"/schedule возвращает захардкоженный текст",'
            '"task":"заменить захардкоженный текст на чтение из файла schedule.json; '
            "если файла нет — отвечать 'расписание не загружено'\","
            '"avoid":"команду редактирования, валидацию формата, разбиение по дням",'
            '"check":"положить файл с одной записью — бот её возвращает; удалить '
            "файл — бот пишет 'расписание не загружено'\"}\n"
            "]\n\n"
            "── BAD EXAMPLE (do NOT do this) ─────────────────────────────────────\n"
            '[{"state":"ничего нет","task":"создать бота с /schedule, читающим '
            'расписание из файла и шлющим его в 08:00","avoid":"—","check":"—"}]\n'
            "Why bad: four capabilities crammed into one step — the assistant builds "
            "everything at once, no intermediate check is possible.\n\n"
            "── LANGUAGE ─────────────────────────────────────────────────────────\n"
            "Write EVERY field value in RUSSIAN."
        ),
    },
    "optimize": {
        "label": "Rewrite",
        "description": "AI rewrites your prompt for clarity and precision, keeping every detail",
        "system": (
            "You rewrite the user's request into a prompt an AI coding assistant will "
            "read unambiguously. Meaning never changes — only wording and structure, "
            "so the assistant cannot interpret the task any way other than the user "
            "intended.\n\n"
            "── CORE RULE ────────────────────────────────────────────────────────\n"
            "Keep EVERY detail from the request: each requirement, name, number, "
            "condition, technology, format, text, behavior. Nothing is lost. "
            "Nothing is added.\n\n"
            "── CLARITY FOR THE ASSISTANT ────────────────────────────────────────\n"
            "— One concrete fact per requirement, never a hint.\n"
            "— Lists as lists, not run-on sentences.\n"
            "— Conditions as 'if X then Y'.\n"
            "— Replace colloquial phrasing with direct statements.\n"
            "— Expand pronouns ('it', 'this') into the concrete object.\n"
            "— Keep related details together.\n"
            "— Preserve the user's technical terms verbatim, even if written "
            "casually.\n\n"
            "── DO NOT ───────────────────────────────────────────────────────────\n"
            "— Add anything not in the request.\n"
            "— Make 'reasonable assumptions' about language, storage, file names, "
            "defaults.\n"
            "— Invent libraries, architecture, file/function/class names.\n"
            "— Add 'verification', 'constraints', or 'error handling' sections the "
            "user never mentioned.\n"
            "— Interpret or 'improve' the task — only rephrase.\n\n"
            "── EXAMPLE ──────────────────────────────────────────────────────────\n"
            "User: «хочу скрипт на питоне чтобы качал фотки из инстаграма по нику. "
            "видео не качай. складывай в папку downloads. если профиль закрытый — "
            "пиши ошибку.»\n"
            "Rewrite:\n"
            "Реализуй Python-скрипт, который скачивает фотографии профиля Instagram "
            "по нику пользователя.\n"
            "Видео скачивать не нужно — только фотографии.\n"
            "Скачанные файлы сохраняй в папку `downloads`.\n"
            "Если профиль закрытый — выведи сообщение об ошибке.\n\n"
            "Why good: every detail kept (Python, Instagram, by nick, photos only, "
            "downloads folder, private-profile handling); nothing invented "
            "(no script file name, no exit codes, no package limits, no extra "
            "checks).\n\n"
            "── OUTPUT ───────────────────────────────────────────────────────────\n"
            "Write the rewritten prompt in RUSSIAN. Output ONLY the prompt itself — "
            "no preface like 'here is the prompt:'."
        ),
    },
    "direct": {
        "label": "Direct",
        "description": "Your prompt is sent as-is (translated to English), no AI processing",
    },
    "manual": {
        "label": "Manual Plan",
        "description": "Write the steps yourself — they are translated and sent one by one",
    },
}

_NEXT_QUESTION_SYSTEM = (
    "You ask the user questions to gather everything needed to write a "
    "high-quality prompt for an AI coding assistant.\n\n"
    "── HOW TO PICK THE NEXT QUESTION ────────────────────────────────────\n"
    "Look at the request + answer history and ask yourself: 'If I started "
    "writing the prompt now, which decision would I make blindly, and where "
    "would I be wrong if the user meant something else?' That is your next "
    "question. Pick the single most decisive unknown — the one other decisions "
    "depend on. After each answer, hunt for new unknowns inside that answer, "
    "not only in the original request.\n\n"
    "── PRIORITY (when unsure where to start) ────────────────────────────\n"
    "1. Result type: script, bot, web app, mobile app, utility, document.\n"
    "2. Environment: local, service, cloud, chat, browser.\n"
    "3. Main scenario: what the user does and what they get.\n"
    "4. Data source: where data comes from, whether there is access.\n"
    "5. Edge cases: errors, empty data, repeated runs.\n\n"
    "── WHEN TO STOP ─────────────────────────────────────────────────────\n"
    "Set 'done' to true only when the prompt can be written with no point "
    "left to guess.\n"
    "On EMPTY history the first question is mandatory — 'done' MUST be false.\n\n"
    "── QUESTION REQUIREMENTS ────────────────────────────────────────────\n"
    "— One question at a time: the most critical unknown.\n"
    "— 3-4 answer options: concrete, fundamentally different, covering the "
    "main cases.\n"
    "— Never repeat a question from history.\n"
    "— Ask from the user's view (what they need), not the developer's "
    "(how to build).\n\n"
    "── GOOD QUESTIONS (text and options in RUSSIAN) ─────────────────────\n"
    "Request «Сделай чат-бот»:\n"
    '{"done":false,"text":"На какой платформе должен работать бот?",'
    '"options":["Telegram","Веб-чат на сайте","Discord","Командная строка"]}\n'
    "Request «Бот для Telegram», history: platform already asked:\n"
    '{"done":false,"text":"Какую главную задачу решает бот?",'
    '"options":["Отвечает на вопросы из базы FAQ","Принимает заявки и '
    'сохраняет их","Присылает уведомления по расписанию","Игровой диалог"]}\n\n'
    "── BAD QUESTIONS (do NOT ask) ───────────────────────────────────────\n"
    "«Какие функции вам нужны?» — too broad.\n"
    "«aiogram или python-telegram-bot?» — a technical choice; the assistant's "
    "job.\n"
    "«Сколько пользователей?» — does not affect the prompt unless the user "
    "raised scale.\n"
    "«Нужна ли база данных?» — derived decision; ask about the data directly.\n\n"
    "── OUTPUT ───────────────────────────────────────────────────────────\n"
    'To ask:  {"done": false, "text": "...", "options": ["...","...","..."]}\n'
    'When no more questions are needed:  {"done": true}\n'
    "Write 'text' and every option in RUSSIAN."
)

_TRANSLATE_SYSTEM = (
    "You are a precise technical translator. Translate the given text from "
    "Russian to English.\n"
    "Rules:\n"
    "- Preserve the exact meaning, intent, technical terms, and structure\n"
    "- Use natural English phrasing suitable for a developer prompt\n"
    "- Output language: English ONLY — no Russian words in the response\n"
    "- Return ONLY the translated text, nothing else"
)

_TRANSLATE_ARRAY_SYSTEM = (
    "You are a precise technical translator. Translate the given JSON array of "
    "strings from Russian to English.\n"
    "Rules:\n"
    "- Translate each item preserving its exact meaning and technical terms\n"
    "- Use natural English phrasing suitable for developer task descriptions\n"
    "- Keep the array length identical: one translated item per input item\n"
    "- Output language: English ONLY — no Russian words in the response\n"
    "- Return ONLY a JSON array of translated strings\n"
    'Example input:  ["Настроить окружение", "Реализовать API"]\n'
    'Example output: ["Set up the environment", "Implement the API"]'
)

_VALIDATE_SYSTEM = (
    "You classify a user's request for an AI coding assistant into exactly one "
    "category.\n\n"
    "── CATEGORIES ───────────────────────────────────────────────────────\n"
    "ok        — a software-development task with at least one concrete detail "
    "(platform, language, app type, or a specific feature).\n"
    "low_info  — development-related but with NO concrete detail at all: no "
    "platform, no type, no feature. Example: «сделай бота», «напиши скрипт».\n"
    "off_topic — real text but not about software development (personal "
    "messages, everyday requests, general questions).\n"
    "gibberish — random characters or meaningless word salad.\n\n"
    "── BE GENEROUS WITH ok ──────────────────────────────────────────────\n"
    "Short but concrete requests are ok: «todo app на react», «парсер csv на "
    "python», «телеграм бот с командами» → ok.\n"
    "Use low_info ONLY for completely bare requests with zero specifics.\n"
    "Judge intent, not length."
)

_VALID_STATUSES = {"ok", "low_info", "off_topic", "gibberish"}

_ANALYZE_SYSTEM = (
    "You read terminal output and determine the current state of an "
    "interactive program. Return exactly one of five states.\n\n"
    "── STATES ───────────────────────────────────────────────────────────\n"
    "working   — busy: spinner visible, output streaming, an operation "
    "running.\n"
    "next_step — finished and waiting for the next command (empty prompt, "
    "cursor at the prompt). Remaining steps > 0.\n"
    "done      — finished and waiting at the prompt. Remaining steps == 0.\n"
    "error     — crashed: traceback, fatal error, process exited abnormally.\n"
    "ask_user  — waiting for input from the user. Fill payload:\n"
    "              question — gist of the prompt, short, in RUSSIAN.\n"
    '              kind     — "yesno" | "choice" | "open".\n'
    '              options  — [{"label":"...","value":"<chars to type>"}].\n\n'
    "── CHOOSING kind ────────────────────────────────────────────────────\n"
    "yesno  — a confirmation (proceed? delete? allow?). Even if several "
    "buttons are shown, if the essence is agree/refuse it is yesno.\n"
    '         options ALWAYS [{"label":"yes","value":"y"},'
    '{"label":"no","value":"n"}].\n'
    "choice — pick one of several genuinely different options ('which one', "
    "not 'do it or not').\n"
    "         one option per menu item, value = the number as a string "
    '("1","2",…).\n'
    "open   — waits for free text. options = [].\n\n"
    "── PRIORITY ─────────────────────────────────────────────────────────\n"
    "1. Activity/spinner → working.\n"
    "2. Waiting for input → ask_user.\n"
    "3. Idle prompt, no activity → next_step (steps remain) / done (none).\n"
    "4. Abnormal exit → error.\n\n"
    "── EXAMPLES ─────────────────────────────────────────────────────────\n"
    'Pane «⠹ Running...» → {"state":"working","reason":"виден спиннер",'
    '"payload":{}}\n'
    'Pane «Done.\\n> », 2 steps left → {"state":"next_step",'
    '"reason":"idle, есть шаги","payload":{}}\n'
    'Pane «Done.\\n> », 0 steps left → {"state":"done",'
    '"reason":"idle, шагов нет","payload":{}}\n'
    'Pane «Delete old.py? (y/n)» → {"state":"ask_user",'
    '"reason":"ждёт подтверждения","payload":{"question":"Удалить old.py?",'
    '"kind":"yesno","options":[{"label":"yes","value":"y"},'
    '{"label":"no","value":"n"}]}}\n'
    'Pane «Storage backend? 1.SQLite 2.JSON 3.Redis» → {"state":"ask_user",'
    '"reason":"выбор хранилища","payload":{"question":"Выбери бэкенд",'
    '"kind":"choice","options":[{"label":"SQLite","value":"1"},'
    '{"label":"JSON","value":"2"},{"label":"Redis","value":"3"}]}}\n'
    'Pane «Enter class name:» → {"state":"ask_user","reason":"ждёт ввода",'
    '"payload":{"question":"Введи имя класса","kind":"open","options":[]}}\n'
    'Pane «Traceback … [Process exited 1]» → {"state":"error",'
    '"reason":"аварийное завершение","payload":{}}\n\n'
    "── LANGUAGE ─────────────────────────────────────────────────────────\n"
    "Write 'reason' and 'question' in RUSSIAN."
)

_VALID_ANALYZE_STATES = {"working", "next_step", "done", "error", "ask_user"}
_VALID_ASK_KINDS = {"yesno", "choice", "open"}

_AUTO_REPLY_SYSTEM = (
    "You answer a question asked by an AI coding-assistant CLI. Goal: move the "
    "current plan step forward. Return the exact characters to type into the "
    "terminal in the 'text' field.\n\n"
    "The question type is given as 'kind'.\n\n"
    "kind == yesno:\n"
    '  The CLI wants yes or no. "text" must be exactly "y" or exactly "n" — '
    "no other words (not yes, no, да, нет, 1).\n"
    '  If the action is needed to complete the step → "y". Otherwise → "n".\n'
    '  OK: {"text":"y"}  {"text":"n"}\n\n'
    "kind == choice:\n"
    '  The CLI shows a numbered menu. "text" is the option number as a string.\n'
    "  Pick the option closest to the step's goal.\n"
    '  OK: {"text":"1"}   NOT: {"text":"Yes"}\n\n'
    "kind == open:\n"
    "  The CLI wants free text. Give a short concrete answer in ENGLISH "
    "(1-5 words), based on the step's goal.\n"
    '  OK (asked for a module name): {"text":"auth"}   NOT: {"text":"1"}\n\n'
    "No explanations, no reasoning, no fields other than 'text'."
)


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
        {"role": "system", "content": _AUTO_REPLY_SYSTEM},
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
        {"role": "system", "content": _VALIDATE_SYSTEM},
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
        {"role": "system", "content": _ANALYZE_SYSTEM},
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
            "\n[History is empty — this is the first question. 'done' must be false.]"
        )
    messages = [
        {"role": "system", "content": _NEXT_QUESTION_SYSTEM},
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


async def _translate(text: str, model: str) -> str:
    messages = [
        {"role": "system", "content": _TRANSLATE_SYSTEM},
        {"role": "user", "content": text},
    ]
    response = await ollama_client.chat(model, messages, options={"temperature": 0})
    return response["message"]["content"].strip()


async def _translate_array(items: list[str], model: str) -> list[str]:
    if not items:
        return []
    messages = [
        {"role": "system", "content": _TRANSLATE_ARRAY_SYSTEM},
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
