"""
Centralized logging setup for ProxyMind backend.

Call setup() once at startup (main.py). Every other module just does:
    from log import logger
"""
import logging
import sys
from pathlib import Path

from loguru import logger

# ── Log file location ────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent.parent.parent / "logs"

# ── Console format ───────────────────────────────────────────────────────────
# Short and scannable: time | coloured level | module:line — message
_CONSOLE_FMT = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
    "<level>{message}</level>"
)

# ── File format ──────────────────────────────────────────────────────────────
# Full ISO timestamp for grep/analysis; no ANSI codes
_FILE_FMT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level:<8} | "
    "{name}:{function}:{line} — "
    "{message}"
)


class _InterceptHandler(logging.Handler):
    """Route stdlib logging (uvicorn, fastapi, httpx, …) through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]

        frame, depth = logging.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup(level: str = "DEBUG") -> None:
    """Configure loguru sinks. Call once at application startup."""
    logger.remove()

    # Console sink — coloured, human-readable
    logger.add(
        sys.stderr,
        level=level,
        format=_CONSOLE_FMT,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File sink — plain text, rotation 10 MB, keep 7 days, compress old files
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        _LOG_DIR / "proxymind.log",
        level="DEBUG",
        format=_FILE_FMT,
        rotation="10 MB",
        retention="7 days",
        compression="gz",
        backtrace=True,
        diagnose=False,  # no sensitive data in files
        encoding="utf-8",
    )

    # Intercept every stdlib logger (uvicorn, fastapi, httpx, libtmux, …)
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = [_InterceptHandler()]
        logging.getLogger(name).propagate = False

    logger.info("Logging ready — console + {}", _LOG_DIR / "proxymind.log")
