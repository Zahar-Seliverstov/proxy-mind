import asyncio

import httpx

import config

# Контекстное окно по умолчанию для всех запросов. Без явного num_ctx Ollama
# берёт значение из Modelfile модели (часто 2048), что на промптах этого
# сервиса (длинные системные инструкции + хвост pane/история уточнений)
# приводит к молчаливой обрезке контекста и деградации ответов модели.
DEFAULT_NUM_CTX = 8192

# Один запрос к Ollama в момент времени. Параллельные чаты к одной и той же
# локальной модели заставляют Ollama переключать контекст/выгружать-загружать
# модель между запросами, из-за чего каждый отдельный запрос становится
# намного медленнее и легче упирается в таймаут.
_SEMAPHORE = asyncio.Semaphore(1)

# 14B-модель на CPU генерирует медленно, особенно под grammar-constrained
# decoding (response_format). 120с слишком мало для длинных ответов (план).
_TIMEOUT_S = 300


def _base_url() -> str:
    return config.get().ollama_base_url.rstrip("/")


async def get_models() -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{_base_url()}/api/tags")
        response.raise_for_status()
        return response.json()["models"]


async def chat(
    model: str,
    messages: list[dict],
    options: dict | None = None,
    response_format: dict | str | None = None,
) -> dict:
    payload_options = {"num_ctx": DEFAULT_NUM_CTX, **(options or {})}
    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": payload_options,
    }
    if response_format is not None:
        payload["format"] = response_format
    async with _SEMAPHORE:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.post(f"{_base_url()}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
