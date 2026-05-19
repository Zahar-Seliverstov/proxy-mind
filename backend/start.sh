#!/bin/sh
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/http_server"
exec ../.venv/bin/python main.py
cd "$(dirname "$0")/telegram_bot"
exec ../.venv/bin/python main.py
