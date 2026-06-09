#!/usr/bin/env python3
import ctypes
import ctypes.util
import os
import random
import sys
import time


def _set_proc_name(name: str) -> None:
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c"))
        libc.prctl(15, name.encode(), 0, 0, 0)
    except Exception:
        pass


_set_proc_name("claude")

DIM    = "\033[2m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BLUE   = "\033[34m"
MAGENTA = "\033[35m"
RESET  = "\033[0m"

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

VERBS = [
    "Thinking", "Reasoning", "Analyzing", "Planning", "Synthesizing",
    "Pondering", "Reflecting", "Evaluating", "Deliberating", "Computing",
]


# ── primitives ────────────────────────────────────────────────────────────────

def write(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


def banner() -> None:
    cwd = os.getcwd()
    if len(cwd) > 36:
        cwd = "…" + cwd[-35:]
    box = [
        "╭───────────────────────────────────────────────╮",
        "│ ✻ Welcome to Claude Code (fake REPL).         │",
        "│                                               │",
        "│   model: claude-opus-4.7                      │",
        f"│   cwd:   {cwd:<37}│",
        "│                                               │",
        "│   /help for help, /exit to quit               │",
        "╰───────────────────────────────────────────────╯",
    ]
    write("\n".join(box) + "\n\n")


def prompt() -> None:
    write(f"\n{CYAN}❯{RESET} ")


def spinner(seconds: float = 2.0, verb: str | None = None) -> None:
    verb = verb or random.choice(VERBS)
    start = time.time()
    i = 0
    while time.time() - start < seconds:
        frame = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
        elapsed = int(time.time() - start)
        suffix = f"for {elapsed}s" if elapsed > 0 else ""
        write(f"\r{CYAN}{frame}{RESET} {DIM}{verb} {suffix}{RESET}   ")
        time.sleep(0.1)
        i += 1
    write("\r" + " " * 60 + "\r")


def bullet(text: str, color: str = GREEN) -> None:
    write(f"{color}●{RESET} {text}\n")


def tool_call(name: str, detail: str = "") -> None:
    line = f"{BLUE}●{RESET} {BOLD}{name}{RESET}"
    if detail:
        line += f" {DIM}{detail}{RESET}"
    write(line + "\n")


def tool_out(text: str) -> None:
    write(f"  {DIM}⎿  {text}{RESET}\n")


def tool_out_block(lines: list[str]) -> None:
    for line in lines:
        write(f"  {DIM}⎿  {line}{RESET}\n")


def section(title: str) -> None:
    write(f"\n{BOLD}{CYAN}{title}{RESET}\n")


def thinking(text: str) -> None:
    write(f"{DIM}  ↳ {text}{RESET}\n")


def read_line() -> str:
    try:
        return sys.stdin.readline()
    except KeyboardInterrupt:
        write("\n^C\n")
        sys.exit(0)


def ask_yesno(question: str) -> bool:
    write(f"\n{BOLD}{question}{RESET} (y/n) ")
    answer = read_line().strip().lower()
    write("\n")
    return answer.startswith("y")


def ask_menu(title: str, command: str, options: list[str]) -> str:
    box_width = max(len(title), len(command), max(len(o) for o in options)) + 6
    w = max(box_width, 54)
    write("\n")
    write("╭" + "─" * w + "╮\n")
    write(f"│ {title:<{w-2}}│\n")
    write(f"│   {DIM}{command}{RESET:<{w-5}}   │\n")
    write("│" + " " * w + "│\n")
    write(f"│ {'Do you want to proceed?':<{w-2}}│\n")
    for i, opt in enumerate(options, 1):
        marker = "❯" if i == 1 else " "
        write(f"│ {marker} {i}. {opt:<{w-6}}│\n")
    write("╰" + "─" * w + "╯\n")
    answer = read_line().strip()
    write("\n")
    return answer


def ask_open(question: str) -> str:
    write(f"\n{question}\n{CYAN}❯{RESET} ")
    answer = read_line().strip()
    write("\n")
    return answer


# ── scenes ────────────────────────────────────────────────────────────────────

def scene_read_and_edit() -> None:
    spinner(1.8, "Analyzing")
    tool_call("Read", "src/api/routes.py")
    tool_out("187 lines")
    spinner(1.2, "Planning")
    tool_call("Read", "src/models/user.py")
    tool_out("64 lines")
    thinking("endpoint missing input validation, adding pydantic schema")
    spinner(1.4, "Editing")
    tool_call("Edit", "src/api/routes.py")
    tool_out("12 insertions, 3 deletions")
    tool_call("Edit", "src/models/user.py")
    tool_out("5 insertions")
    write("\n")
    bullet("Added input validation to the user endpoint using Pydantic schemas.")


def scene_yesno() -> None:
    spinner(1.8, "Thinking")
    bullet("I need to overwrite the existing config to apply the new settings.")
    if ask_yesno("Overwrite config/settings.yaml with updated values?"):
        tool_call("Write", "config/settings.yaml")
        tool_out("written 34 lines")
        spinner(0.6, "Verifying")
        tool_call("Bash", "python -c \"import yaml; yaml.safe_load(open('config/settings.yaml'))\"")
        tool_out("syntax OK")
        bullet("Config updated and validated.")
    else:
        bullet("Skipped — keeping the original config.")


def scene_menu() -> None:
    spinner(2.0, "Planning")
    bullet("Need to reinstall dependencies to pick up the new packages.")
    ans = ask_menu(
        "Bash command",
        "rm -rf node_modules && npm install",
        [
            "Yes",
            "Yes, and don't ask again for npm commands",
            "No, and tell Claude what to do differently",
        ],
    )
    if ans in ("1", "2"):
        tool_call("Bash", "rm -rf node_modules && npm install")
        spinner(3.0, "Installing")
        tool_out("added 487 packages in 18.4s")
        bullet("Dependencies reinstalled successfully.")
    else:
        bullet("Skipped — dependencies unchanged.")


def scene_open() -> None:
    spinner(1.5, "Designing")
    bullet("I'm ready to scaffold the new service module.")
    name = ask_open("What should we call the new service? (e.g. notifications, billing, auth)")
    name = name or "service"
    spinner(1.2, "Writing")
    tool_call("Write", f"src/services/{name}.py")
    tool_out("created — 42 lines")
    tool_call("Write", f"tests/test_{name}.py")
    tool_out("created — 28 lines")
    bullet(f"Scaffolded {BOLD}src/services/{name}.py{RESET} with basic structure and test file.")


def scene_error() -> None:
    spinner(1.5, "Running")
    tool_call("Bash", "pytest tests/ -x")
    spinner(1.0, "Testing")
    write(f"\n{RED}FAILED tests/test_api.py::test_create_user — AssertionError{RESET}\n")
    write(f"{RED}Traceback (most recent call last):{RESET}\n")
    write('  File "tests/test_api.py", line 47, in test_create_user\n')
    write("    assert response.status_code == 201\n")
    write(f"{RED}AssertionError: assert 422 == 201{RESET}\n")
    write("[Process exited with code 1]\n")
    sys.exit(1)


def scene_working_long() -> None:
    bullet("Starting full project build — this will take a moment…")
    spinner(4.0, "Compiling")
    tool_call("Bash", "make build")
    tool_out("compiled 91 files")
    spinner(3.5, "Linking")
    tool_out("build succeeded in 7.2s")
    tool_call("Bash", "make test")
    spinner(4.0, "Testing")
    tool_out("47 passed, 0 failed in 3.9s")
    bullet("Build and tests passed.")


def scene_permission_chain() -> None:
    spinner(1.2, "Planning")
    bullet("This step requires three shell operations.")

    for cmd, desc, out in [
        ("git add -A",             "Bash command", "staged 17 files"),
        ("git commit -m 'feat: ...'", "Bash command", "[main a1b2c3d] feat: implement new endpoint"),
        ("git push origin main",   "Bash command", "Branch 'main' → 'origin/main'"),
    ]:
        ans = ask_menu(desc, cmd, [
            "Yes",
            "Yes, and don't ask again for git commands",
            "No, and tell Claude what to do differently",
        ])
        if ans not in ("1", "2"):
            bullet(f"Stopped at: {cmd}")
            return
        tool_call("Bash", cmd)
        tool_out(out)

    bullet("Committed and pushed successfully.")


def scene_debug_investigate() -> None:
    spinner(2.0, "Analyzing")
    section("Investigating the failing request…")
    tool_call("Read", "src/middleware/auth.py")
    tool_out("103 lines")
    thinking("token expiry check uses UTC naive datetime — likely timezone mismatch")
    tool_call("Bash", "grep -n 'datetime.now' src/middleware/auth.py")
    tool_out_block([
        "42:    if token.expires_at < datetime.now():",
        "67:    token.created_at = datetime.now()",
    ])
    spinner(1.0, "Confirming")
    tool_call("Bash", "python -c \"from datetime import datetime,timezone; print(datetime.now(timezone.utc))\"")
    tool_out("2026-06-09 14:22:01.443210+00:00")
    thinking("confirmed — replacing naive datetime.now() with datetime.now(timezone.utc)")
    spinner(1.2, "Fixing")
    tool_call("Edit", "src/middleware/auth.py")
    tool_out("2 lines changed")
    tool_call("Bash", "pytest tests/test_auth.py -v")
    spinner(1.5, "Testing")
    tool_out_block([
        "test_valid_token     PASSED",
        "test_expired_token   PASSED",
        "test_missing_token   PASSED",
        "3 passed in 0.8s",
    ])
    write("\n")
    bullet("Fixed timezone bug — all auth tests passing.")


def scene_multi_file_refactor() -> None:
    spinner(2.5, "Reading codebase")
    files = [
        ("src/handlers/user.py",    "214 lines"),
        ("src/handlers/order.py",   "178 lines"),
        ("src/handlers/product.py", "196 lines"),
        ("src/utils/db.py",         "88 lines"),
    ]
    for path, size in files:
        tool_call("Read", path)
        tool_out(size)

    spinner(1.5, "Planning refactor")
    thinking("db session management duplicated in all three handlers — extract to dependency")
    write("\n")
    bullet("I'll extract the database session logic into a shared dependency.")
    bullet("This affects 3 handler files and adds a new utils/dependencies.py.")
    write("\n")

    if not ask_yesno("Proceed with refactoring all 3 handlers?"):
        bullet("Aborted — no changes made.")
        return

    spinner(1.8, "Refactoring")
    tool_call("Write", "src/utils/dependencies.py")
    tool_out("created — 31 lines")
    for path, changes in [
        ("src/handlers/user.py",    "18 deletions, 4 insertions"),
        ("src/handlers/order.py",   "17 deletions, 4 insertions"),
        ("src/handlers/product.py", "19 deletions, 4 insertions"),
    ]:
        tool_call("Edit", path)
        tool_out(changes)

    spinner(1.2, "Verifying")
    tool_call("Bash", "python -m pytest tests/ -q")
    tool_out("62 passed in 2.1s")
    write("\n")
    bullet("Refactor complete — session logic centralized, all tests green.")


def scene_write_tests() -> None:
    spinner(1.5, "Reading source")
    tool_call("Read", "src/services/pricing.py")
    tool_out("127 lines")
    tool_call("Read", "tests/test_pricing.py")
    tool_out("file not found — will create")
    thinking("need to cover: calculate_discount, apply_vat, final_price edge cases")
    spinner(1.8, "Writing tests")
    tool_call("Write", "tests/test_pricing.py")
    tool_out("created — 84 lines, 11 test cases")
    tool_call("Bash", "pytest tests/test_pricing.py -v")
    spinner(2.0, "Running")
    tool_out_block([
        "test_discount_zero_percent     PASSED",
        "test_discount_hundred_percent  PASSED",
        "test_vat_standard_rate         PASSED",
        "test_vat_reduced_rate          PASSED",
        "test_final_price_with_discount PASSED",
        "test_final_price_negative_qty  PASSED",
        "test_final_price_zero_price    PASSED",
        "test_bulk_pricing_threshold    PASSED",
        "test_bulk_pricing_below        PASSED",
        "test_currency_rounding         PASSED",
        "test_invalid_discount_raises   PASSED",
        "11 passed in 0.4s",
    ])
    write("\n")
    bullet("Test suite for pricing service written — 11 tests, 100% of public methods covered.")


def scene_api_scaffold() -> None:
    spinner(2.0, "Planning")
    section("Scaffolding new API endpoint…")

    topic = ask_open(
        "What resource should the endpoint manage?\n"
        "  1. products\n"
        "  2. orders\n"
        "  3. reviews\n"
        "Enter number or custom name:"
    )
    resource = {"1": "products", "2": "orders", "3": "reviews"}.get(topic, topic or "items")

    spinner(1.5, "Generating")
    for path, desc in [
        (f"src/schemas/{resource}.py",  "Pydantic schemas — created 38 lines"),
        (f"src/routers/{resource}.py",  "Router with CRUD — created 94 lines"),
        (f"tests/test_{resource}.py",   "Test suite — created 61 lines"),
    ]:
        tool_call("Write", path)
        tool_out(desc)

    tool_call("Edit", "src/main.py")
    tool_out(f"added: app.include_router({resource}_router)")

    spinner(1.0, "Testing")
    tool_call("Bash", f"pytest tests/test_{resource}.py -q")
    tool_out("9 passed in 0.6s")
    write("\n")
    bullet(f"Endpoint /{resource} scaffolded with schema, router, and tests.")


def scene_dependency_audit() -> None:
    spinner(1.5, "Scanning")
    tool_call("Bash", "pip list --outdated")
    tool_out_block([
        "Package      Version  Latest",
        "fastapi      0.109.0  0.115.2",
        "httpx        0.26.0   0.28.1",
        "pydantic     2.5.3    2.11.4",
        "sqlalchemy   2.0.25   2.0.41",
    ])
    thinking("4 packages outdated — pydantic and sqlalchemy are major-version-safe, updating all")

    ans = ask_menu(
        "Bash command",
        "pip install --upgrade fastapi httpx pydantic sqlalchemy",
        [
            "Yes",
            "Yes, and don't ask again for pip commands",
            "No, skip the upgrade",
        ],
    )
    if ans not in ("1", "2"):
        bullet("Skipped — dependencies unchanged.")
        return

    tool_call("Bash", "pip install --upgrade fastapi httpx pydantic sqlalchemy")
    spinner(2.5, "Upgrading")
    tool_out("Successfully upgraded 4 packages")
    tool_call("Bash", "pytest tests/ -q --tb=short")
    spinner(2.0, "Regression check")
    tool_out("74 passed in 3.2s")
    write("\n")
    bullet("All dependencies upgraded, no regressions detected.")


def scene_schema_migration() -> None:
    spinner(2.0, "Analyzing schema diff")
    tool_call("Read", "database/models.py")
    tool_out("152 lines")
    tool_call("Bash", "alembic current")
    tool_out("a3f9c1b2d4e5 (head)")
    thinking("users table missing 'last_login' and 'is_verified' columns")

    bullet("Schema is out of sync — two columns missing from users table.")

    if not ask_yesno("Generate and apply Alembic migration?"):
        bullet("Skipped — schema unchanged.")
        return

    spinner(1.5, "Generating")
    tool_call("Bash", "alembic revision --autogenerate -m 'add_last_login_is_verified'")
    tool_out("generated migrations/versions/b7d2e3f1a4c8_.py")
    tool_call("Read", "migrations/versions/b7d2e3f1a4c8_.py")
    tool_out("29 lines — adds columns with nullable=True, no data loss")

    ans = ask_menu(
        "Bash command",
        "alembic upgrade head",
        [
            "Yes, apply migration",
            "No, review migration first",
        ],
    )
    if ans == "1":
        tool_call("Bash", "alembic upgrade head")
        spinner(1.0, "Migrating")
        tool_out("b7d2e3f1a4c8 → head (head)")
        bullet("Migration applied — users table updated.")
    else:
        bullet("Migration generated but not applied. Review migrations/versions/b7d2e3f1a4c8_.py first.")


def scene_code_review() -> None:
    spinner(2.5, "Reviewing")
    section("Code review findings:")

    issues = [
        (YELLOW, "warn",  "src/api/orders.py:83   — N+1 query in order items loop"),
        (YELLOW, "warn",  "src/utils/cache.py:41  — TTL hardcoded to 300s, should be configurable"),
        (RED,    "error", "src/auth/tokens.py:17  — secret key read from os.environ without fallback"),
        (GREEN,  "info",  "src/models/product.py  — well structured, no issues"),
    ]
    for color, level, msg in issues:
        write(f"  {color}[{level}]{RESET} {msg}\n")

    write("\n")
    bullet(f"Found {RED}1 critical{RESET}, {YELLOW}2 warnings{RESET}.")

    if ask_yesno("Fix the critical issue (missing env fallback) now?"):
        spinner(0.8, "Fixing")
        tool_call("Edit", "src/auth/tokens.py")
        tool_out("line 17: added fallback with ValueError on missing key")
        tool_call("Bash", "grep -n 'SECRET_KEY' src/auth/tokens.py")
        tool_out('17:    secret = os.environ.get("SECRET_KEY") or raise ValueError("SECRET_KEY not set")')
        bullet("Critical issue fixed. Warnings can be addressed separately.")
    else:
        bullet("Noted — please fix src/auth/tokens.py:17 before deploying.")


def scene_rate_limit() -> None:
    spinner(1.5, "Thinking")
    tool_call("Read", "src/api/routes.py")
    tool_out("142 lines")
    spinner(1.2, "Planning")
    tool_call("Edit", "src/api/routes.py")
    tool_out("added rate limiting middleware")
    spinner(1.0, "Verifying")
    tool_call("Bash", "pytest tests/test_routes.py -q")
    spinner(2.8, "Running tests")
    write("\n")
    write(f"{RED}API Error: Rate limit exceeded. You have exceeded your rate limit of 50 requests/min.\n")
    write(f"Please wait before retrying. Resets in 60 seconds.{RESET}\n")
    write(f"{DIM}(request throttled by Anthropic API){RESET}\n")


def scene_billing_limit() -> None:
    spinner(2.0, "Analyzing")
    tool_call("Read", "src/services/payment.py")
    tool_out("98 lines")
    tool_call("Read", "src/models/transaction.py")
    tool_out("61 lines")
    thinking("refactoring transaction flow to use atomic DB operations")
    spinner(1.6, "Planning")
    tool_call("Edit", "src/services/payment.py")
    tool_out("rewrote process_payment to use db.transaction()")
    spinner(1.0, "Writing tests")
    tool_call("Write", "tests/test_payment.py")
    tool_out("18 lines")
    spinner(2.2, "Running")
    tool_call("Bash", "pytest tests/test_payment.py -v")
    spinner(1.8, "Testing")
    write("\n")
    write(f"{RED}╭─────────────────────────────────────────────────────╮\n")
    write(f"│  Insufficient credits                               │\n")
    write(f"│                                                     │\n")
    write(f"│  You have run out of API credits.                   │\n")
    write(f"│  Please upgrade your plan or add billing details    │\n")
    write(f"│  at console.anthropic.com to continue.              │\n")
    write(f"╰─────────────────────────────────────────────────────╯{RESET}\n")


def scene_quota_mid_step() -> None:
    spinner(1.8, "Analyzing project structure")
    tool_call("Bash", "find src/ -name '*.py' | head -20")
    tool_out_block([
        "src/api/routes.py", "src/api/middleware.py",
        "src/models/user.py", "src/models/order.py",
        "src/services/auth.py", "src/services/email.py",
    ])
    thinking("need to add authentication to 6 route handlers")
    spinner(1.2, "Reading")
    tool_call("Read", "src/api/routes.py")
    tool_out("187 lines")
    tool_call("Read", "src/services/auth.py")
    tool_out("74 lines")
    spinner(2.0, "Editing")
    tool_call("Edit", "src/api/routes.py")
    tool_out("added @require_auth to /orders, /profile, /settings")
    tool_call("Edit", "src/api/middleware.py")
    tool_out("registered AuthMiddleware in app factory")
    spinner(1.0, "Continuing")
    tool_call("Read", "src/models/user.py")
    tool_out("61 lines")
    write("\n")
    write(f"{YELLOW}Warning: You are approaching your usage limit (95% consumed).{RESET}\n")
    spinner(1.4, "Processing")
    write("\n")
    write(f"{RED}Error: quota exceeded — monthly token limit reached.\n")
    write(f"Usage cap hit. Please wait until the limit resets or upgrade your plan.{RESET}\n")


# ── scenarios ─────────────────────────────────────────────────────────────────

SCENARIOS: dict[str, list] = {
    # original compact scenarios
    "mixed": [
        scene_read_and_edit,
        scene_yesno,
        scene_menu,
        scene_open,
        scene_read_and_edit,
    ],
    "next_step":        [scene_read_and_edit] * 5,
    "yesno":            [scene_yesno, scene_read_and_edit],
    "menu":             [scene_menu, scene_read_and_edit],
    "open":             [scene_open, scene_read_and_edit],
    "error":            [scene_read_and_edit, scene_error],
    "working_long":     [scene_working_long, scene_read_and_edit],
    "permission_chain": [scene_permission_chain, scene_read_and_edit],

    # new complex scenarios
    "debug": [
        scene_read_and_edit,
        scene_debug_investigate,
        scene_write_tests,
    ],
    "refactor": [
        scene_read_and_edit,
        scene_multi_file_refactor,
        scene_write_tests,
        scene_yesno,
    ],
    "api_build": [
        scene_read_and_edit,
        scene_api_scaffold,
        scene_dependency_audit,
        scene_permission_chain,
    ],
    "review": [
        scene_code_review,
        scene_debug_investigate,
        scene_read_and_edit,
    ],
    "migration": [
        scene_read_and_edit,
        scene_schema_migration,
        scene_write_tests,
        scene_permission_chain,
    ],
    "full": [
        scene_read_and_edit,
        scene_debug_investigate,
        scene_multi_file_refactor,
        scene_api_scaffold,
        scene_write_tests,
        scene_dependency_audit,
        scene_code_review,
        scene_permission_chain,
    ],

    # limit scenarios
    "limit_rate":    [scene_read_and_edit, scene_rate_limit],
    "limit_billing": [scene_read_and_edit, scene_billing_limit],
    "limit_quota":   [scene_read_and_edit, scene_quota_mid_step],
    "limit": [
        scene_read_and_edit,
        scene_quota_mid_step,
    ],
}


def main() -> None:
    scenario = sys.argv[1] if len(sys.argv) > 1 else "mixed"
    scenes = SCENARIOS.get(scenario)
    if scenes is None:
        avail = ", ".join(SCENARIOS)
        write(f"{RED}unknown scenario '{scenario}'.{RESET}\navailable: {avail}\n")
        sys.exit(2)

    write(f"{DIM}(fake claude — scenario: {scenario}, {len(scenes)} scenes){RESET}\n")
    banner()
    prompt()

    i = 0
    while True:
        line = read_line()
        if not line:
            sys.exit(0)
        line = line.strip()
        if line in ("/exit", "/quit"):
            write("bye.\n")
            sys.exit(0)
        if line == "/help":
            write(
                f"{DIM}commands: /exit, /help\n"
                f"scenarios: {', '.join(SCENARIOS)}{RESET}\n"
            )
            prompt()
            continue

        write("\n")
        scene = scenes[i % len(scenes)]
        scene()
        i += 1
        prompt()


if __name__ == "__main__":
    main()
