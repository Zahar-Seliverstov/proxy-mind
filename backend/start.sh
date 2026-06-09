#!/bin/sh
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")"
# exec replaces this shell with the API server.
exec .venv/bin/python main.py
