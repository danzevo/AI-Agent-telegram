import httpx
from config import settings

class LLMService:
    def __init__(self):
        self.base_url = settings.lm_studio_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def get_embedding(self, text: str) -> list[float]:
        response = await self.client.post(f"{self.base_url}/embeddings",
                            json={
                                "input": text,
                                "model": "nomic-embed-text-v1.5"
                            })

        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    async def chat_completion(self, messages: list[dict]) -> dict:
        payload = {
            "model": "llama-3-8b-instruct",
            "messages": messages,
            "temperature": 0.3
        }
        response = await self.client.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]
        