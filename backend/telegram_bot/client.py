import httpx

_BASE_URL = "https://api.telegram.org"


async def send_message(token: str, chat_id: str, text: str) -> dict:
    url = f"{_BASE_URL}/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
