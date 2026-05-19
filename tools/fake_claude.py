#!/usr/bin/env python3
"""Fake Claude Code REPL — local stand-in for testing the orchestrator
without burning real model calls.

Renames its own process to "claude" via prctl so the sessions panel
(which filters by pane_current_command == "claude") picks it up.

Run inside a tmux pane:
    python tools/fake_claude.py [scenario]

Scenarios (each is a sequence of scenes played one per orchestrator step):
    mixed         (default) rotates yesno / menu / open / normal / error
    next_step     every step succeeds cleanly
    yesno         classic (y/n) confirmation
    menu          Claude Code style permission menu (boxed, numbered)
    open          open-ended question with no options
    error         step crashes with a traceback
    working_long  extended spinner before completion
    permission_chain  two permission menus in a row
"""
import ctypes
import ctypes.util
import os
import random
import sys
import time


# ── make tmux report process name as "claude" ─────────────────────
def _set_proc_name(name: str) -> None:
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c"))
        libc.prctl(15, name.encode(), 0, 0, 0)  # PR_SET_NAME = 15
    except Exception:
        pass


_set_proc_name("claude")


# ── ANSI helpers ─────────────────────────────────────────────────
DIM    = "\033[2m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BLUE   = "\033[34m"
RESET  = "\033[0m"

VERBS = [
    "Cogitating", "Pondering", "Synthesizing", "Musing", "Reasoning",
    "Contemplating", "Reflecting", "Deliberating", "Wrangling", "Brewing",
]

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


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


def spinner(seconds: float = 2, verb: str | None = None) -> None:
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
    line = f"{BLUE}●{RESET} {name}"
    if detail:
        line += f" {DIM}{detail}{RESET}"
    write(line + "\n")


def tool_out(text: str) -> None:
    write(f"  {DIM}⎿  {text}{RESET}\n")


def read_line() -> str:
    try:
        return sys.stdin.readline()
    except KeyboardInterrupt:
        write("\n^C\n")
        sys.exit(0)


# ── scenes ───────────────────────────────────────────────────────
# Each scene reacts to ONE incoming step prompt. It may also block on
# additional input() if the scene asks the user something mid-step.

def scene_normal_step() -> None:
    spinner(2.5)
    tool_call("Read", "package.json")
    tool_out("42 lines")
    spinner(1.2, "Editing")
    tool_call("Edit", "src/handler.ts")
    tool_out("8 insertions, 2 deletions")
    write("\n")
    bullet("Done. Added the requested handler — endpoint returns the new payload format.")


def scene_yesno() -> None:
    spinner(1.8, "Thinking")
    bullet("I need to delete the old config before continuing.")
    write(f"\n{BOLD}Delete /tmp/old.config and continue?{RESET} (y/n) ")
    answer = read_line().strip().lower()
    write("\n")
    if answer.startswith("y"):
        tool_call("Bash", "rm /tmp/old.config")
        tool_out("removed '/tmp/old.config'")
        spinner(0.8, "Continuing")
        bullet("Done.")
    else:
        bullet("Skipped — kept the old config.")


def scene_menu() -> None:
    spinner(2, "Planning")
    bullet("I'd like to run a shell command.")
    write("\n")
    box = [
        "╭────────────────────────────────────────────────────╮",
        "│ Bash command                                       │",
        "│   rm -rf node_modules && npm install               │",
        "│                                                    │",
        "│ Do you want to proceed?                            │",
        "│ ❯ 1. Yes                                           │",
        "│   2. Yes, and don't ask again for npm commands     │",
        "│   3. No, and tell Claude what to do differently    │",
        "╰────────────────────────────────────────────────────╯",
    ]
    write("\n".join(box) + "\n")
    answer = read_line().strip()
    write("\n")
    if answer in ("1", "2"):
        tool_call("Bash", "rm -rf node_modules && npm install")
        spinner(2.5, "Running")
        tool_out("added 412 packages in 14s")
        bullet("Done — dependencies reinstalled.")
    else:
        bullet("OK, skipped the install. Let me know how you'd like to handle it.")


def scene_open() -> None:
    spinner(1.5, "Designing")
    bullet("I'm ready to create the new module — what should we name it?")
    write(f"\n{CYAN}❯{RESET} ")
    answer = read_line().strip()
    write("\n")
    name = answer or "module"
    tool_call("Write", f"src/{name}.ts")
    tool_out("created")
    spinner(0.8, "Writing")
    bullet(f"Done — created {BOLD}src/{name}.ts{RESET}.")


def scene_error() -> None:
    spinner(1.5, "Calling")
    write(f"{RED}Traceback (most recent call last):{RESET}\n")
    write('  File "/usr/lib/claude/tool.py", line 142, in run_tool\n')
    write("    return self._invoke()\n")
    write('  File "/usr/lib/claude/tool.py", line 87, in _invoke\n')
    write("    response = requests.post(url, json=payload)\n")
    write(f"{RED}ConnectionError: [Errno 111] Connection refused{RESET}\n")
    write("[Process exited with code 1]\n")
    sys.exit(1)


def scene_working_long() -> None:
    bullet("Starting long-running task…")
    spinner(6, "Building")
    tool_call("Bash", "make build")
    tool_out("compiled 47 files in 5.8s")
    bullet("Done.")


def scene_double_menu() -> None:
    spinner(1.2, "Planning")
    bullet("Two permissions needed for this step.")

    write("\n")
    box1 = [
        "╭────────────────────────────────────────────────────╮",
        "│ Bash command                                       │",
        "│   git add -A                                       │",
        "│                                                    │",
        "│ Do you want to proceed?                            │",
        "│ ❯ 1. Yes                                           │",
        "│   2. Yes, and don't ask again for git commands     │",
        "│   3. No, and tell Claude what to do differently    │",
        "╰────────────────────────────────────────────────────╯",
    ]
    write("\n".join(box1) + "\n")
    a1 = read_line().strip()
    write("\n")
    if a1 not in ("1", "2"):
        bullet("OK, skipped — aborting step.")
        return
    tool_call("Bash", "git add -A")
    tool_out("staged 12 files")

    write("\n")
    box2 = [
        "╭────────────────────────────────────────────────────╮",
        "│ Bash command                                       │",
        "│   git commit -m 'wip'                              │",
        "│                                                    │",
        "│ Do you want to proceed?                            │",
        "│ ❯ 1. Yes                                           │",
        "│   2. Yes, and don't ask again for git commands     │",
        "│   3. No, and tell Claude what to do differently    │",
        "╰────────────────────────────────────────────────────╯",
    ]
    write("\n".join(box2) + "\n")
    a2 = read_line().strip()
    write("\n")
    if a2 in ("1", "2"):
        tool_call("Bash", "git commit -m 'wip'")
        tool_out("[main 9f3a2b1] wip")
        bullet("Done — staged and committed.")
    else:
        bullet("Staged, but skipped the commit.")


# ── scenarios ────────────────────────────────────────────────────

SCENARIOS: dict[str, list] = {
    "mixed":             [scene_normal_step, scene_yesno, scene_menu, scene_open, scene_normal_step],
    "next_step":         [scene_normal_step] * 5,
    "yesno":             [scene_yesno, scene_normal_step],
    "menu":              [scene_menu, scene_normal_step],
    "open":              [scene_open, scene_normal_step],
    "error":             [scene_normal_step, scene_error],
    "working_long":      [scene_working_long, scene_normal_step],
    "permission_chain":  [scene_double_menu, scene_normal_step],
}


def main() -> None:
    scenario = sys.argv[1] if len(sys.argv) > 1 else "mixed"
    scenes = SCENARIOS.get(scenario)
    if scenes is None:
        write(f"{RED}unknown scenario '{scenario}'. available: {', '.join(SCENARIOS)}{RESET}\n")
        sys.exit(2)

    write(f"{DIM}(fake claude — scenario: {scenario}){RESET}\n")
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
            write(f"{DIM}commands: /exit, /help. just type a prompt and I'll play the next scene.{RESET}\n")
            prompt()
            continue

        write("\n")
        scene = scenes[i % len(scenes)]
        scene()
        i += 1
        prompt()


if __name__ == "__main__":
    main()
