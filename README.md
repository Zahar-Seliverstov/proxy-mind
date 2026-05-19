# ProxyMind

**ProxyMind** — веб-интерфейс для автоматизированного управления AI-ассистентами кода (Claude Code, Aider и др.), работающими в терминальных сессиях tmux.

## Что это такое

Вместо того чтобы вручную копировать промпты в терминал, следить за выводом и отвечать на вопросы CLI — ProxyMind делает это за вас. Вы формулируете задачу в браузере, система разбивает её на шаги и последовательно выполняет их через AI-ассистент.

```
Браузер (Vue 3)  ──►  Backend (FastAPI)  ──►  Ollama (LLM)
                              │
                              ▼
                         tmux (libtmux)
                              │
                              ▼
                     Claude Code / Aider
```

## Возможности

- **Auto Plan** — AI разбивает задачу на 3–8 проверяемых шагов, задаёт уточняющие вопросы перед стартом
- **Rewrite** — AI переформулирует размытый промпт чётко и однозначно
- **Direct** — промпт переводится на английский и отправляется как есть
- **Manual Plan** — вы пишете шаги сами, система переводит и выполняет по очереди
- **Оркестратор** — автоматически отвечает на вопросы CLI (y/n, выбор меню), определяет зависания
- **RunMonitor** — лог выполнения в реальном времени, пауза / продолжение / отмена
- **Telegram-уведомления** — опционально, при завершении задачи

## Стек технологий

| Слой | Технологии |
|---|---|
| Frontend | Vue 3, Vite, Pinia, Axios |
| Backend | Python 3.10+, FastAPI, uvicorn |
| AI-интеграция | Ollama REST API (qwen2.5-coder:14b) |
| Терминал | libtmux |
| Уведомления | Telegram Bot API |

## Быстрый старт

### Требования

- Python 3.10+
- Node.js 18+
- tmux
- [Ollama](https://ollama.com) с моделью `qwen2.5-coder:14b`

### Установка

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Запуск

```bash
# Терминал 1 — backend (порт 3000)
cd backend && ./start.sh

# Терминал 2 — frontend (порт 5173)
cd frontend && npm run dev
```

Открыть браузер: **http://localhost:5173**

### Telegram-бот (опционально)

```bash
cd backend && ./start_telegram.sh
```

Настроить токен и chat_id через кнопку ⚙️ в интерфейсе.

## Структура проекта

```
nmnt/
├── backend/
│   ├── http_server/
│   │   ├── main.py               # FastAPI, порт 3000
│   │   ├── routers/              # ai, tmux, fs, ollama, settings
│   │   ├── services/
│   │   │   ├── ai.py             # AI-логика, промпты, Ollama-вызовы
│   │   │   └── orchestrator.py   # оркестратор — конечный автомат выполнения
│   │   └── clients/ollama/       # async httpx-клиент
│   └── telegram_bot/             # FastAPI, порт 3001
├── frontend/
│   └── src/
│       ├── components/           # 12 Vue-компонентов
│       ├── stores/               # Pinia: sessions, notifications
│       └── api/                  # axios-обёртки
├── tools/
│   └── fake_claude.py            # симулятор CLI для тестирования
└── docs/
    ├── uml/                      # PlantUML-диаграммы
    ├── user_manual.md
    ├── admin_manual.md
    └── test_protocol.md
```

## Настройка

Файл настроек создаётся автоматически: `~/.config/proxymind/settings.json`

```json
{
  "ollama_base_url": "http://localhost:11434",
  "telegram_bot_token": "",
  "telegram_chat_id": ""
}
```

## Тестирование без реального AI

```bash
# Запустить симулятор в tmux-панели:
python tools/fake_claude.py [сценарий]

# Сценарии: mixed, next_step, yesno, menu, open, error, working_long, permission_chain
```

## Документация

- [Руководство пользователя](docs/user_manual.md)
- [Руководство администратора](docs/admin_manual.md)
- [Протокол тестирования](docs/test_protocol.md)

## Автор

Селиверстов Захар Александрович — преддипломная практика, Академия ТОП, 2026
