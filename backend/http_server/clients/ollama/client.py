import httpx

import config


def _base_url() -> str:
    return config.get().ollama_base_url.rstrip("/")


async def get_models() -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{_base_url()}/api/tags")
        response.raise_for_status()
        return response.json()["models"]


async def chat(model: str, messages: list[dict], options: dict | None = None) -> dict:
    payload: dict = {"model": model, "messages": messages, "stream": False}
    if options:
        payload["options"] = options
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(f"{_base_url()}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()
