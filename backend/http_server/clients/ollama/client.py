import httpx

import config


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
    payload: dict = {"model": model, "messages": messages, "stream": False}
    if options:
        payload["options"] = options
    if response_format is not None:
        # Ollama structured outputs: a JSON schema (dict) or the string "json".
        # Constrains generation at the grammar level — the model cannot emit
        # text outside the schema, which is critical for small (7-14B) models.
        payload["format"] = response_format
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(f"{_base_url()}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()
