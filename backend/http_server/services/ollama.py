from clients.ollama import client as ollama_client


async def get_models() -> list[str]:
    models = await ollama_client.get_models()
    return [m["name"] for m in models]
