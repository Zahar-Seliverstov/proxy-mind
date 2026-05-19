import json
from clients.ollama import client as ollama_client


def _extract_obj(raw: str) -> dict | None:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def _extract_arr(raw: str) -> list | None:
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


MODES = {
    "plan": {
        "label": "Auto Plan",
        "description": "AI breaks your task into small verifiable steps and runs them one by one",
        "system": (
            "Ты разбиваешь запрос пользователя на цепочку промптов для AI-ассистента кода.\n"
            "Промпты должны быть такими, чтобы реализация шла маленькими проверяемыми итерациями.\n\n"
            "── ПРОБЛЕМА КОТОРУЮ РЕШАЕМ ──────────────────────────────────────────\n"
            "AI-ассистент кода делает всё что упомянуто в промпте плюс «что логично заодно».\n"
            "Если в одном промпте написано «сделай бота с расписанием» — он реализует всё за раз,\n"
            "без промежуточных проверок, ошибки копятся и переплетаются.\n"
            "Решение: каждый промпт = одна возможность + явный запрет на всё остальное.\n\n"
            "── СТРУКТУРА КАЖДОГО ПРОМПТА (цельный текст, без markdown) ──────────\n"
            "Состояние: что уже работает после предыдущего шага.\n"
            "Задача: одна возможность которую нужно добавить и как она ведёт себя.\n"
            "Не делать: то что относится к следующим шагам и сейчас не нужно.\n"
            "Проверка: одно конкретное действие, по которому видно что возможность работает.\n\n"
            "── ГРАНИЦА ОТВЕТСТВЕННОСТИ ──────────────────────────────────────────\n"
            "Описываешь ЧТО нужно и КАК ДОЛЖНО ВЕСТИ СЕБЯ.\n"
            "НЕ описываешь: библиотеки, имена файлов/функций/классов, архитектуру кода.\n"
            "Технологии и имена — только те, что назвал сам пользователь.\n\n"
            "── ПРИМЕР ХОРОШЕГО ПЛАНА ────────────────────────────────────────────\n"
            "Запрос: «Telegram-бот, который присылает расписание»\n"
            "[\n"
            "  \"Состояние: ничего нет. Задача: создать Telegram-бот, который на команду /start отвечает строкой 'бот работает'. Не делать: другие команды, хранилище, меню, обработку любых других сообщений. Проверка: написать боту /start — приходит ответ 'бот работает'.\",\n"
            "  \"Состояние: бот отвечает на /start строкой 'бот работает'. Задача: добавить команду /schedule, которая возвращает три захардкоженные строки расписания через разделитель ' | ' (например 'Пн: матан 9:00 | Вт: физика 11:00 | Ср: химия 13:00'). Не делать: чтение из файла, разбиение по дням, сохранение состояния. Проверка: /schedule возвращает эти три строки.\",\n"
            "  \"Состояние: /schedule возвращает захардкоженный текст. Задача: заменить захардкоженный текст на чтение из файла schedule.json — массив объектов с полями day, subject, time; если файла нет — бот отвечает 'расписание не загружено'. Не делать: команду редактирования, валидацию формата, разбиение по дням. Проверка: положить файл с одной записью — бот её возвращает; удалить файл — бот пишет 'расписание не загружено'.\",\n"
            "  \"Состояние: бот возвращает расписание из файла по команде /schedule. Задача: добавить автоматическую отправку текущего расписания каждое утро в 08:00 каждому пользователю, который хотя бы раз писал /start; список пользователей хранить рядом с расписанием. Не делать: настройку времени отправки, отписку, фильтрацию по дням недели. Проверка: запустить бот в 07:59, дождаться 08:00 — все писавшие /start получают расписание автоматически.\"\n"
            "]\n\n"
            "── ПОЧЕМУ ЭТО ХОРОШО ────────────────────────────────────────────────\n"
            "— Каждый шаг можно запустить и увидеть результат отдельно от остальных.\n"
            "— В каждом шаге явный запрет — AI физически не «убегает вперёд».\n"
            "— Состояние ссылается на предыдущий шаг — последовательность жёсткая, не перепутаешь.\n"
            "— Структура работает для любой области: веб, скрипты, мобильные приложения, игры, автоматизация.\n\n"
            "── ПЛОХОЙ ПРИМЕР (так НЕ делать) ────────────────────────────────────\n"
            "[\"Создай Telegram-бот с командой /schedule, который читает расписание из файла и присылает его в 08:00\"]\n"
            "Почему плохо: четыре возможности в одном шаге — AI реализует всё сразу,\n"
            "промежуточные проверки невозможны, при сбое непонятно где сломалось.\n\n"
            "── КОЛИЧЕСТВО ШАГОВ ─────────────────────────────────────────────────\n"
            "Обычно 3–8. Слишком крупный = несколько возможностей в одном шаге.\n"
            "Слишком мелкий = результат нельзя проверить отдельно от соседних шагов.\n\n"
            "── УЧТИ ВСЁ ─────────────────────────────────────────────────────────\n"
            "Каждое уточнение пользователя должно появиться в промпте — ни одна деталь не теряется.\n"
            "Если пользователь сказал «на Python» — пиши Python. Если сказал «использовать Redis» — пиши Redis.\n"
            "Сам ничего не выдумывай.\n\n"
            "Язык: ТОЛЬКО русский.\n"
            "Формат: ТОЛЬКО валидный JSON-массив строк. Никакого текста за пределами массива."
        ),
    },
    "optimize": {
        "label": "Rewrite",
        "description": "AI rewrites your prompt for clarity and precision, keeping every detail",
        "system": (
            "Ты переписываешь запрос пользователя в промпт, максимально понятный для AI-ассистента кода.\n"
            "Содержание не меняется. Меняются только слова и формат — так, чтобы AI прочитал их\n"
            "однозначно и не имел шанса понять задачу иначе, чем задумал пользователь.\n\n"
            "── ГЛАВНОЕ ПРАВИЛО ──────────────────────────────────────────────────\n"
            "Сохраняешь КАЖДУЮ деталь из запроса, включая самые мелкие.\n"
            "Каждое требование, имя, число, условие, технология, формат, текст, поведение,\n"
            "упомянутые пользователем — обязаны попасть в финальный промпт.\n"
            "Ни одна деталь не теряется. Ни одна деталь не добавляется.\n\n"
            "── ПОНЯТНОСТЬ ДЛЯ AI ────────────────────────────────────────────────\n"
            "Финальный промпт должен читаться машиной без двусмысленностей.\n"
            "— Каждое требование выражено одним конкретным фактом, а не намёком.\n"
            "— Перечисления — списком, а не сплошным предложением через запятую.\n"
            "— Условия в форме «если X — то Y», а не «ну там типа когда X».\n"
            "— Разговорные обороты («чтоб», «хотелось бы», «прикольно если») заменяются на прямые формулировки.\n"
            "— Местоимения раскрываются: «он», «оно», «это» заменяются на конкретный объект.\n"
            "— Связанные детали стоят рядом; не разбросаны по тексту.\n"
            "— Технические термины пользователя сохраняются дословно, даже если он написал их в просторечной форме.\n\n"
            "── ЧЕГО ТЫ НЕ ДЕЛАЕШЬ ───────────────────────────────────────────────\n"
            "Не добавляешь ничего, чего не было в запросе.\n"
            "Не делаешь «разумных предположений»: про язык, хранилище, имена файлов, поведение по умолчанию.\n"
            "Не выдумываешь библиотеки, архитектуру, имена файлов/функций/классов.\n"
            "Не добавляешь разделы «Проверка», «Ограничения», «Поведение при ошибке»,\n"
            "если про это ничего не сказано в запросе.\n"
            "Не интерпретируешь задачу и не «улучшаешь» её — только переформулируешь.\n\n"
            "── КАК ПЕРЕФОРМУЛИРОВАТЬ ────────────────────────────────────────────\n"
            "Директивный стиль: «реализуй», «создай», «используй» — не «можно было бы», «желательно».\n"
            "Однозначные формулировки вместо разговорных и размытых.\n"
            "Группируешь связанные детали в смысловые блоки — но только те блоки,\n"
            "для которых в запросе есть содержимое. Никаких пустых заголовков.\n"
            "Без markdown-заголовков, цельный текст с короткими абзацами или списком.\n\n"
            "── ПРИМЕР ───────────────────────────────────────────────────────────\n"
            "Запрос пользователя:\n"
            "«хочу скрипт на питоне чтобы качал фотки из инстаграма по нику. видео не качай.\n"
            "складывай в папку downloads. если профиль закрытый — пиши ошибку.»\n\n"
            "Переформулированный промпт:\n"
            "Реализуй Python-скрипт, который скачивает фотографии профиля Instagram по нику пользователя.\n"
            "Видео скачивать не нужно — только фотографии.\n"
            "Скачанные файлы сохраняй в папку `downloads`.\n"
            "Если профиль закрытый — выведи сообщение об ошибке.\n\n"
            "── ПОЧЕМУ ЭТО ХОРОШО ────────────────────────────────────────────────\n"
            "— Все детали из запроса сохранены: Python, Instagram, по нику, только фото,\n"
            "  папка downloads, обработка закрытого профиля.\n"
            "— Ничего лишнего: нет имени файла скрипта, нет кодов выхода, нет формата итога,\n"
            "  нет ограничений на пакеты, нет проверки — пользователь про это не говорил.\n"
            "— Каждое требование — отдельной строкой, без «и», «а ещё», «чтоб».\n"
            "— Условие про закрытый профиль выражено явной формой «если — то».\n"
            "— AI не сможет прочитать это иначе, чем задумано.\n\n"
            "── ПЛОХОЙ ПРИМЕР (так НЕ делать) ────────────────────────────────────\n"
            "Для того же запроса:\n"
            "«Локальный Python-скрипт, запускается командой `python download.py <username>`.\n"
            "Сохраняй в `./downloads/<username>/`, имя файла = id публикации с расширением .jpg.\n"
            "Если файл уже есть — пропускай. При отсутствии интернета — выход с кодом 2.\n"
            "Без GUI, веб-сервера, БД. Только print в консоль.»\n"
            "Почему плохо: имя файла `download.py`, формат пути, имя файла = id публикации,\n"
            "коды выхода, обработка интернета, ограничения на GUI/БД — ничего этого\n"
            "в запросе не было. Это домыслы, а не переформулировка.\n\n"
            "── ЯЗЫК И ФОРМАТ ────────────────────────────────────────────────────\n"
            "Язык: ТОЛЬКО русский.\n"
            "Формат: ТОЛЬКО готовый промпт. Без вступлений вроде «вот промпт:» или «промпт ниже:»."
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
    "Ты задаёшь пользователю вопросы, чтобы собрать всё нужное для написания качественного промпта AI-ассистенту кода.\n\n"
    "── ПРИНЦИП ВЫБОРА ВОПРОСА ───────────────────────────────────────────\n"
    "Смотришь на запрос + историю ответов и спрашиваешь себя:\n"
    "«Если я сейчас начну писать промпт — какое решение я приму вслепую,\n"
    "и где ошибусь, если пользователь имел в виду другое?»\n"
    "Это и есть следующий вопрос.\n\n"
    "Среди всех неизвестных бери самое весомое — то, от которого зависят остальные решения.\n"
    "Получил ответ — ищи новые точки выбора в нём, а не только в исходном запросе.\n\n"
    "── ПОРЯДОК ПРИОРИТЕТА (если непонятно с чего начать) ────────────────\n"
    "1. Тип результата: скрипт, бот, веб-приложение, мобильное приложение, утилита, документ\n"
    "2. Среда работы: локально, как сервис, в облаке, в чате, в браузере\n"
    "3. Главный сценарий: что пользователь делает и что получает\n"
    "4. Источник данных: откуда берутся данные, есть ли к ним доступ\n"
    "5. Граничные сценарии: ошибки, пустые данные, повторные запуски\n\n"
    "── КОГДА ОСТАНОВИТЬСЯ (null) ────────────────────────────────────────\n"
    "Когда промпт можно написать и в нём нет ни одной точки где ты что-то предполагаешь.\n"
    "При пустой истории: первый вопрос обязателен — null запрещён.\n\n"
    "── ТРЕБОВАНИЯ К ВОПРОСУ ─────────────────────────────────────────────\n"
    "Один вопрос за раз — самый критичный из неизвестных.\n"
    "3–4 варианта ответа: конкретных, принципиально разных, покрывающих основные случаи.\n"
    "Не повторяй вопросы из истории.\n"
    "Спрашивай с позиции пользователя (что нужно), а не разработчика (как делать).\n\n"
    "── ПРИМЕРЫ ХОРОШИХ ВОПРОСОВ ─────────────────────────────────────────\n"
    "Запрос: «Сделай чат-бот»\n"
    '{"text": "На какой платформе должен работать бот?", "options": ["Telegram", "Веб-чат на сайте", "Discord", "Командная строка"]}\n\n'
    "Запрос: «Бот для Telegram». История: спросили про платформу.\n"
    '{"text": "Какую главную задачу решает бот?", "options": ["Отвечает на вопросы из базы FAQ", "Принимает заявки и сохраняет их", "Присылает уведомления по расписанию", "Игровой диалог с пользователем"]}\n\n'
    "Запрос: «Бот для Telegram присылает уведомления». История: платформа Telegram, задача — уведомления.\n"
    '{"text": "Что именно и когда бот присылает?", "options": ["Расписание раз в день в фиксированное время", "Новости из RSS по мере появления", "Напоминания которые пользователь сам задаёт", "Курс валют или погоду по запросу"]}\n\n'
    "── ПЛОХИЕ ВОПРОСЫ (так НЕ делать) ───────────────────────────────────\n"
    "«Какие функции вам нужны?» — слишком широкий, не уточняет конкретный выбор.\n"
    "«aiogram или python-telegram-bot?» — техническое решение, это работа AI-ассистента.\n"
    "«Сколько пользователей будет?» — не влияет на промпт, пока пользователь не упомянет масштаб.\n"
    "«Нужна ли база данных?» — производное решение, спрашивай про данные напрямую.\n\n"
    "Язык: ТОЛЬКО русский.\n\n"
    "ФОРМАТ — только JSON, никакого текста снаружи:\n"
    '{"text": "текст вопроса", "options": ["вариант 1", "вариант 2", "вариант 3"]}\n'
    "или: null"
)

_TRANSLATE_SYSTEM = (
    "You are a precise technical translator. Translate the given text from Russian to English.\n"
    "Rules:\n"
    "- Preserve the exact meaning, intent, technical terms, and structure\n"
    "- Use natural English phrasing suitable for a developer prompt\n"
    "- Output language: English ONLY — no Russian words in the response\n"
    "- Return ONLY the translated text, nothing else"
)

_TRANSLATE_ARRAY_SYSTEM = (
    "You are a precise technical translator. Translate the given JSON array of strings from Russian to English.\n"
    "Rules:\n"
    "- Translate each item preserving its exact meaning and technical terms\n"
    "- Use natural English phrasing suitable for developer task descriptions\n"
    "- Output language: English ONLY — no Russian words in the response\n"
    "- Return ONLY a valid JSON array of translated strings, no other text\n"
    'Example input:  ["Настроить окружение", "Реализовать API"]\n'
    'Example output: ["Set up the environment", "Implement the API"]'
)

_VALIDATE_SYSTEM = (
    "Ты классифицируешь запрос пользователя для AI-ассистента кода.\n\n"
    "── КАТЕГОРИИ ────────────────────────────────────────────────────────\n"
    "ok        — запрос описывает задачу разработки и достаточно информативен.\n"
    "low_info  — запрос про разработку, но слишком абстрактный: нет ни платформы,\n"
    "            ни типа задачи, ни единой детали. Пример: «сделай бота» без уточнений.\n"
    "off_topic — настоящий текст, но не про разработку: личные сообщения, бытовые просьбы,\n"
    "            вопросы не по теме программирования.\n"
    "gibberish — случайные символы или бессмысленный набор слов без какого-либо смысла.\n\n"
    "── ВАЖНО ────────────────────────────────────────────────────────────\n"
    "Будь либеральным с ok — короткие но конкретные запросы это ok:\n"
    "«todo app на react», «парсер csv на python», «телеграм бот с командами» → ok.\n"
    "low_info только для совсем голых запросов: «сделай приложение», «напиши скрипт».\n\n"
    "Ответ — ТОЛЬКО JSON, без текста снаружи:\n"
    '{"status": "ok"} | {"status": "low_info"} | {"status": "off_topic"} | {"status": "gibberish"}'
)

_VALID_STATUSES = {"ok", "low_info", "off_topic", "gibberish"}

_ANALYZE_SYSTEM = (
    "Ты анализируешь вывод терминала и определяешь текущее состояние интерактивной программы.\n"
    "Верни одно из пяти состояний.\n\n"
    "── СОСТОЯНИЯ ────────────────────────────────────────────────────────\n"
    "working   — программа активна: виден спиннер, идёт вывод, выполняется операция.\n\n"
    "next_step — программа завершила работу и ждёт следующей команды (пустой prompt,\n"
    "            курсор на приглашении). Оставшихся шагов больше нуля.\n\n"
    "done      — программа завершила работу и ждёт команды. Оставшихся шагов ноль.\n\n"
    "error     — программа упала: traceback, fatal error, процесс завершился аварийно.\n\n"
    "ask_user  — программа ждёт ввода от пользователя.\n"
    "            payload: {\n"
    '              "question": "<суть вопроса, кратко по-русски>",\n'
    '              "kind":     "yesno" | "choice" | "open",\n'
    '              "options":  [{"label": "<текст>", "value": "<ввод в терминал>"}, ...]\n'
    "            }\n\n"
    "            kind — по смыслу запроса:\n"
    '            • yesno  — подтверждение действия: «выполнить?», «удалить?», «разрешить?».\n'
    "                       Неважно сколько вариантов показано — если суть бинарная\n"
    "                       (согласиться / отказаться), это yesno.\n"
    '                       options всегда: [{"label":"yes","value":"y"},{"label":"no","value":"n"}]\n'
    '            • choice — выбор одного из нескольких содержательно разных вариантов\n'
    "                       («что именно делать», а не «делать или нет»).\n"
    '                       options: один элемент на пункт, value = номер строкой ("1","2",…).\n'
    '            • open   — программа ждёт произвольный текст. options = [].\n\n'
    "── ПРИОРИТЕТ ────────────────────────────────────────────────────────\n"
    "1. Активность/спиннер → working.\n"
    "2. Ожидание ввода → ask_user.\n"
    "3. Idle-prompt, нет активности → next_step (шаги есть) или done (шагов нет).\n"
    "4. Аварийное завершение → error.\n\n"
    "── ПРИМЕРЫ ──────────────────────────────────────────────────────────\n"
    "Pane: «⠹ Running...»\n"
    '→ {"state":"working","reason":"виден спиннер","payload":{}}\n\n'
    "Pane: «Done.\\n> » — шагов осталось 2.\n"
    '→ {"state":"next_step","reason":"программа в idle, есть шаги","payload":{}}\n\n'
    "Pane: «Done.\\n> » — шагов осталось 0.\n"
    '→ {"state":"done","reason":"программа в idle, шагов нет","payload":{}}\n\n'
    "Pane: «Delete old.py? (y/n)»\n"
    '→ {"state":"ask_user","reason":"ждёт подтверждения удаления","payload":{\n'
    '  "question":"Удалить old.py?","kind":"yesno",\n'
    '  "options":[{"label":"yes","value":"y"},{"label":"no","value":"n"}]}}\n\n'
    "Pane: запрос разрешения выполнить команду, варианты Yes / Yes always / No.\n"
    '→ {"state":"ask_user","reason":"ждёт разрешения на выполнение","payload":{\n'
    '  "question":"Выполнить команду?","kind":"yesno",\n'
    '  "options":[{"label":"yes","value":"y"},{"label":"no","value":"n"}]}}\n\n'
    "Pane: «Storage backend?\\n  1. SQLite\\n  2. JSON\\n  3. Redis»\n"
    '→ {"state":"ask_user","reason":"выбор из вариантов хранилища","payload":{\n'
    '  "question":"Выбери бэкенд хранилища","kind":"choice",\n'
    '  "options":[{"label":"SQLite","value":"1"},{"label":"JSON","value":"2"},{"label":"Redis","value":"3"}]}}\n\n'
    "Pane: «Enter class name:»\n"
    '→ {"state":"ask_user","reason":"ждёт произвольного ввода","payload":{\n'
    '  "question":"Введи имя класса","kind":"open","options":[]}}\n\n'
    "Pane: «Traceback … ConnectionError … [Process exited 1]»\n"
    '→ {"state":"error","reason":"аварийное завершение","payload":{}}\n\n'
    "ФОРМАТ — только JSON, никакого текста снаружи:\n"
    '{"state":"<state>","reason":"<фраза>","payload":{…}}'
)

_VALID_ANALYZE_STATES = {"working", "next_step", "done", "error", "ask_user"}
_VALID_ASK_KINDS = {"yesno", "choice", "open"}

_AUTO_REPLY_SYSTEM = (
    "Ты отвечаешь на вопрос CLI-ассистента кода. Цель — продвинуть текущий шаг плана к выполнению.\n\n"
    "Верни ТОЛЬКО JSON-объект {\"text\": \"...\"}. Никакого другого текста.\n\n"
    "── ЧТО ПИСАТЬ В ПОЛЕ text ──────────────────────────────────────────────\n\n"
    "Тип вопроса передаётся в поле kind.\n\n"
    "Если kind == yesno:\n"
    "  CLI ждёт «да» или «нет». text должен быть ровно \"y\" или ровно \"n\".\n"
    "  Никаких других слов — ни yes, ни no, ни yesno, ни да, ни нет.\n"
    "  Если действие нужно для выполнения шага — \"y\". Иначе — \"n\".\n"
    "  Правильный пример: {\"text\": \"y\"}\n"
    "  Правильный пример: {\"text\": \"n\"}\n"
    "  НЕПРАВИЛЬНО:       {\"text\": \"yes\"}, {\"text\": \"yesno\"}, {\"text\": \"1\"}\n\n"
    "Если kind == choice:\n"
    "  CLI показывает пронумерованное меню. text — номер варианта строкой.\n"
    "  Выбирай вариант, ближайший к цели шага.\n"
    "  Правильный пример (из трёх пунктов): {\"text\": \"1\"}\n"
    "  НЕПРАВИЛЬНО: {\"text\": \"Yes\"}, {\"text\": \"choice\"}\n\n"
    "Если kind == open:\n"
    "  CLI ждёт произвольный текст. Дай короткий конкретный ответ по-английски (1–5 слов).\n"
    "  Опирайся на цель шага — что именно там требуется сделать.\n"
    "  Правильный пример (CLI спросил имя модуля): {\"text\": \"auth\"}\n"
    "  НЕПРАВИЛЬНО: {\"text\": \"1\"}, {\"text\": \"open\"}\n\n"
    "Никаких пояснений, рассуждений и полей кроме text."
)


async def decide_reply(
    pane_text: str,
    current_step: str,
    remaining_steps: list[str],
    ask: dict,
    model: str,
) -> str:
    options_str = ""
    if ask.get("options"):
        options_str = "\n".join(
            f'  - label="{o.get("label","")}", value="{o.get("value","")}"'
            for o in ask["options"]
        )
    parts = [
        f"Текущий шаг плана: {current_step}",
        f"Оставшихся шагов после текущего: {len(remaining_steps)}",
    ]
    if remaining_steps:
        parts.append("Тексты оставшихся шагов:")
        for i, s in enumerate(remaining_steps, 1):
            parts.append(f"{i}. {s}")
    parts += [
        "",
        "Вопрос CLI:",
        ask.get("question", ""),
        f'kind: {ask.get("kind", "open")}',
    ]
    if options_str:
        parts += ["Варианты:", options_str]
    parts += [
        "",
        "Содержимое pane (последние строки):",
        "```",
        pane_text.strip() or "(pane пуст)",
        "```",
    ]
    messages = [
        {"role": "system", "content": _AUTO_REPLY_SYSTEM},
        {"role": "user", "content": "\n".join(parts)},
    ]
    response = await ollama_client.chat(model, messages, options={"num_predict": 200})
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
                valid = {str(o.get("value", "")).strip() for o in ask.get("options", [])}
                if text in valid:
                    return text
            else:
                return text
    # фолбэк
    if kind == "yesno":
        return "y"
    if kind == "choice" and ask.get("options"):
        return str(ask["options"][0].get("value") or "1")
    return ""


async def validate(prompt: str, mode: str, model: str) -> dict:
    messages = [
        {"role": "system", "content": _VALIDATE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]
    response = await ollama_client.chat(model, messages, options={"num_predict": 32})
    parsed = _extract_obj(response["message"]["content"].strip())
    status = (parsed or {}).get("status")
    if status in _VALID_STATUSES:
        if status == "low_info" and mode != "plan":
            status = "ok"
        return {"status": status}
    return {"status": "ok"}


async def analyze(
    pane_text: str,
    current_step: str,
    remaining_steps: list[str],
    model: str,
) -> dict:
    parts = [
        "Содержимое pane (последние строки терминала):",
        "```",
        pane_text.strip() or "(pane пуст)",
        "```",
        "",
        f"Текущий шаг плана: {current_step}",
        f"Оставшихся шагов после текущего: {len(remaining_steps)}",
    ]
    if remaining_steps:
        parts.append("Тексты оставшихся шагов:")
        for i, s in enumerate(remaining_steps, 1):
            parts.append(f"{i}. {s}")
    messages = [
        {"role": "system", "content": _ANALYZE_SYSTEM},
        {"role": "user", "content": "\n".join(parts)},
    ]
    response = await ollama_client.chat(model, messages, options={"num_predict": 256})
    return _parse_analyze(response["message"]["content"])


def _parse_analyze(raw: str) -> dict:
    parsed = _extract_obj(raw.strip())
    if parsed is None:
        return _ask_fallback("анализатор вернул не-JSON")

    state = parsed.get("state")
    if state not in _VALID_ANALYZE_STATES:
        return _ask_fallback(f"неизвестное состояние '{state}'")

    reason = str(parsed.get("reason", "")).strip() or "без обоснования"
    payload = parsed.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    if state == "ask_user":
        payload = _normalize_ask_payload(payload)

    else:
        payload = {}

    return {"state": state, "reason": reason, "payload": payload}


def _ask_fallback(reason: str) -> dict:
    return {
        "state": "ask_user",
        "reason": reason,
        "payload": {
            "question": "Анализатор не смог понять состояние терминала. Что отправить в pane?",
            "kind": "open",
            "options": [],
        },
    }


def _normalize_ask_payload(payload: dict) -> dict:
    question = str(payload.get("question") or "").strip() or "CLI ждёт ввода — что отправить?"
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


async def get_next_question(prompt: str, mode: str, model: str, history: list[dict]) -> dict:
    mode_hint = MODES.get(mode, {}).get("description", "")
    parts = []
    if mode_hint:
        parts.append(f"Режим генерации: {mode_hint}")
    parts.append(f"Исходный запрос: {prompt}")
    if history:
        parts.append(f"\nИстория уточнений ({len(history)}):")
        for item in history:
            parts.append(f"В: {item['question']}")
            parts.append(f"О: {item['answer']}")
    else:
        parts.append("\n[История пустая — это первый вопрос, верни вопрос, не null]")
    messages = [
        {"role": "system", "content": _NEXT_QUESTION_SYSTEM},
        {"role": "user", "content": "\n".join(parts)},
    ]
    response = await ollama_client.chat(model, messages, options={"num_predict": 256})
    return {"question": _parse_single_question(response["message"]["content"])}


async def generate(prompt: str, mode: str, model: str, answers: list[str] | None = None) -> dict:
    system = MODES[mode]["system"]
    user_content = prompt
    if answers:
        user_content = f"{prompt}\n\nДополнительные уточнения:\n" + "\n".join(f"- {a}" for a in answers)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    response = await ollama_client.chat(model, messages)
    raw = response["message"]["content"]

    if mode == "plan":
        return {"mode": "plan", "steps": _parse_json_array(raw)}

    return {"mode": mode, "result": raw.strip()}


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
    response = await ollama_client.chat(model, messages)
    return response["message"]["content"].strip()


async def _translate_array(items: list[str], model: str) -> list[str]:
    if not items:
        return []
    messages = [
        {"role": "system", "content": _TRANSLATE_ARRAY_SYSTEM},
        {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
    ]
    response = await ollama_client.chat(model, messages)
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
    if parsed and "text" in parsed and "options" in parsed:
        options = [str(o).strip() for o in parsed["options"] if o]
        if options:
            return {"text": str(parsed["text"]).strip(), "options": options}
    return None


def _parse_json_array(raw: str) -> list[str]:
    parsed = _extract_arr(raw.strip())
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if item]
    lines = [line.strip().lstrip("0123456789.-) ") for line in raw.splitlines() if line.strip()]
    return [line for line in lines if line]
