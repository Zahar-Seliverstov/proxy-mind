# ProxyMind

Веб-интерфейс для автоматизированного управления AI-ассистентами кода (Claude Code, Aider и др.), работающими в tmux-сессиях. Пользователь формулирует задачу в браузере — система разбивает её на шаги и последовательно выполняет через CLI-ассистент без ручного вмешательства.

## Требования

| Компонент | Версия |
|---|---|
| ОС | Linux |
| Python | 3.10 и выше |
| Node.js | 18 и выше |
| tmux | 3.0 и выше |
| [Ollama](https://ollama.com) | последняя |
| RAM | от 8 ГБ (модель 7b) / от 16 ГБ (модель 14b) |

## Установка

```bash
# 1. Клонировать репозиторий
git clone <url> proxy-mind
cd proxy-mind

# 2. Python-окружение (backend)
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# 3. Node.js-зависимости (frontend)
cd frontend
npm install
cd ..

# 4. Скачать AI-модель (выполняется один раз)
ollama pull qwen2.5-coder:14b
```

## Запуск

Открыть **два терминала** в папке проекта:

**Терминал 1 — backend (порт 3000):**
```bash
cd backend && ./start.sh
```

**Терминал 2 — frontend (порт 5173):**
```bash
cd frontend && npm run dev
```

Открыть браузер: **http://localhost:5173**

> Ollama должна быть запущена до старта backend: `ollama serve`

## Запуск тестов

```bash
cd backend
.venv/bin/python -m pytest -v
```

54 unit-теста покрывают: очистку ANSI-вывода терминала, нормализацию промптов, хеширование состояния панели, валидацию Pydantic-схем API, логику объединения частей промпта.

## Режимы работы

| Режим | Описание |
|---|---|
| **Auto Plan** | AI разбивает задачу на 3–8 шагов, задаёт уточняющие вопросы перед стартом |
| **Rewrite** | AI переформулирует размытый промпт чётко и отправляет его напрямую |
| **Direct** | Промпт переводится на английский и отправляется как есть |
| **Manual Plan** | Шаги вводятся вручную, система переводит и выполняет по очереди |

## Структура проекта

```
proxy-mind/
├── backend/
│   ├── main.py              # FastAPI, порт 3000
│   ├── routers/             # HTTP-слой: ai, tmux, fs, ollama, settings
│   ├── services/
│   │   ├── ai.py            # AI-логика, промпты, Ollama-вызовы
│   │   └── orchestrator.py  # конечный автомат выполнения
│   ├── database/            # SQLite ORM (SQLAlchemy 2.0, aiosqlite)
│   ├── clients/             # httpx-клиенты: Ollama, Telegram
│   ├── schemas/             # Pydantic-схемы запросов/ответов
│   ├── tests/               # pytest unit-тесты (54 теста)
│   └── start.sh             # скрипт запуска
├── frontend/
│   └── src/
│       ├── components/      # Vue 3 компоненты
│       ├── stores/          # Pinia: sessions, notifications
│       └── api/             # axios-обёртки
└── tools/
    └── fake_claude.py       # симулятор CLI для тестирования оркестратора
```

## Настройки

Файл настроек создаётся автоматически: `~/.config/proxymind/settings.json`

```json
{
  "ollama_base_url": "http://localhost:11434",
  "telegram_bot_token": "",
  "telegram_chat_id": ""
}
```

Настройки меняются через кнопку **Settings** в интерфейсе — перезапуск не нужен.