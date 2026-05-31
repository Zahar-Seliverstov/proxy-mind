#!/bin/sh
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/http_server"
# exec replaces this shell with the API server. The Telegram bot is a separate
# optional service — start it with ./start_telegram.sh.
exec ../.venv/bin/python main.py
