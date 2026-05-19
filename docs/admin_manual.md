# Руководство администратора ProxyMind

**Продукт:** ProxyMind — веб-интерфейс управления AI-ассистентами кода  
**Версия:** 1.0

---

## 1. Системные требования

| Компонент | Требование |
|---|---|
| ОС | Linux (протестировано на Arch/CachyOS) |
| Python | 3.10 и выше |
| Node.js | 18 и выше (рекомендуется 22) |
| tmux | 3.0 и выше |
| Ollama | последняя версия |
| RAM | минимум 8 ГБ (для модели 7b), 16 ГБ (для 14b) |
| Свободный порт | 3000 (backend), 3001 (Telegram-бот), 5173 (frontend dev) |

---

## 2. Установка зависимостей

### 2.1. Python-окружение

```bash
cd nmnt/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # или: pip install fastapi uvicorn libtmux httpx pydantic
```

### 2.2. Node.js-зависимости (frontend)

```bash
cd nmnt/frontend
npm install
```

### 2.3. Ollama

Установить Ollama согласно официальной документации, затем скачать модель:

```bash
ollama pull qwen2.5-coder:14b   # рекомендуемая модель
# или для слабых машин:
ollama pull qwen2.5-coder:7b
```

Проверить, что Ollama запущена:
```bash
curl http://localhost:11434/api/tags
```

---

## 3. Конфигурация

Файл настроек создаётся автоматически при первом сохранении через веб-интерфейс:

**Путь:** `~/.config/proxymind/settings.json`

**Формат:**
```json
{
  "ollama_base_url": "http://localhost:11434",
  "telegram_bot_token": "",
  "telegram_chat_id": ""
}
```

| Параметр | Тип | Описание |
|---|---|---|
| `ollama_base_url` | string | URL Ollama API. Менять если Ollama запущена на другом хосте или порту |
| `telegram_bot_token` | string | Токен Telegram-бота. Получить у @BotFather |
| `telegram_chat_id` | string | ID чата куда слать уведомления. Узнать через @userinfobot |

Файл читается обоими сервисами (backend и telegram_bot) при каждом запросе — перезапуск не нужен после изменений через UI.

---

## 4. Запуск сервисов

### 4.1. HTTP-сервер backend (обязательно)

```bash
cd nmnt/backend
./start.sh
# Сервис запускается на 127.0.0.1:3000
```

Скрипт `start.sh` активирует `.venv` и запускает uvicorn с `reload=True`.

### 4.2. Telegram-бот (опционально)

```bash
cd nmnt/backend
./start_telegram.sh
# Сервис запускается на 127.0.0.1:3001
```

Без Telegram-бота всё работает — уведомления в Telegram просто не отправляются.

### 4.3. Frontend (dev-сервер)

```bash
cd nmnt/frontend
npm run dev
# Сервер запускается на http://localhost:5173
```

Vite автоматически проксирует `/api/*` → `http://localhost:3000`.

### 4.4. Frontend (production-сборка)

```bash
cd nmnt/frontend
npm run build
# Артефакты в frontend/dist/
# Раздать через nginx или любой статический веб-сервер
```

---

## 5. Проверка работоспособности

```bash
# Backend health check
curl http://localhost:3000/
# Ожидается: {"message":"Hello World!","status":"ok"}

# Список сессий tmux
curl http://localhost:3000/api/tmux/sessions

# Список моделей Ollama
curl http://localhost:3000/api/ollama/models
```

---

## 6. Инструмент тестирования оркестратора

Для проверки оркестратора без реального AI используется симулятор:

```bash
# Внутри нужной tmux-панели:
python nmnt/tools/fake_claude.py [сценарий]
```

**Доступные сценарии:**

| Сценарий | Описание |
|---|---|
| `mixed` | Смешанный: next_step, yesno, done |
| `next_step` | Сразу переходит к следующему шагу |
| `yesno` | Запрашивает подтверждение y/n |
| `menu` | Показывает меню выбора |
| `open` | Запрашивает произвольный ввод |
| `error` | Симулирует сбой/traceback |
| `working_long` | Долгое «рабочее» состояние (>30 с) |
| `permission_chain` | Цепочка запросов разрешений |

---

## 7. Структура каталогов

```
nmnt/
├── backend/
│   ├── http_server/
│   │   ├── main.py               # точка входа FastAPI (:3000)
│   │   ├── routers/              # HTTP-слой: ai, tmux, fs, ollama, settings
│   │   ├── services/
│   │   │   ├── ai.py             # AI-логика, промпты, Ollama-вызовы
│   │   │   ├── orchestrator.py   # оркестратор, цикл выполнения
│   │   │   └── tmux/             # libtmux-обёртки
│   │   ├── clients/ollama/       # async httpx-клиент Ollama
│   │   └── schemas/              # Pydantic-схемы запросов/ответов
│   ├── telegram_bot/             # отдельный FastAPI-сервис (:3001)
│   ├── start.sh                  # скрипт запуска backend
│   └── start_telegram.sh         # скрипт запуска Telegram-бота
├── frontend/
│   └── src/
│       ├── components/           # 12 Vue-компонентов
│       ├── stores/               # Pinia: sessions, notifications
│       ├── api/                  # axios-обёртки: ai, tmux, fs, ollama, settings
│       └── views/MainView.vue    # корневой layout
├── tools/
│   └── fake_claude.py            # симулятор CLI для тестирования
└── docs/
    ├── uml/                      # PlantUML-диаграммы
    ├── test_protocol.md          # протокол тестирования
    ├── user_manual.md            # руководство пользователя
    └── admin_manual.md           # настоящий документ
```

---

## 8. Параметры оркестратора (тонкая настройка)

Редактируются напрямую в `backend/http_server/services/orchestrator.py`:

| Константа | Значение | Описание |
|---|---|---|
| `POLL_INTERVAL_S` | 0.3 с | Частота опроса вывода панели |
| `STABLE_MS` | 1500 мс | Время стабильности хэша для признания «завершил» |
| `INITIAL_GRACE_S` | 1.0 с | Пауза после отправки промпта перед началом опроса |
| `MAX_STABLE_WAIT_S` | 30.0 с | Максимальное ожидание стабилизации |
| `PANE_TAIL_LINES` | 200 | Сколько последних строк передаётся анализатору |
| `MAX_AUTO_REPLIES_PER_QUESTION` | 5 | Порог обнаружения зависания |
| `ANALYZE_MAX_RETRIES` | 3 | Повторов при невалидном JSON от LLM |

---

## 9. Известные ограничения

- Одновременно активен максимум **один запуск на панель** (нет глобального лимита между панелями)
- История запусков хранится **in-memory** — теряется при перезапуске backend
- Автоматизированные тесты (unit/integration) отсутствуют — используется `fake_claude.py`
