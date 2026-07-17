import httpx
import asyncio
import os
from config import settings

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class TelegramService:
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.client = httpx.AsyncClient(timeout=30.0, verify=settings.ssl_verify)

    async def set_webhook(self, url: str):
        await self.client.post(f"{self.base_url}/setWebhook", json={"url": url})

    async def delete_webhook(self):
        await self.client.post(f"{self.base_url}/deleteWebhook")

    async def send_message(self, chat_id: int, text: str):
        await self.client.post(f"{self.base_url}/sendMessage", json={"chat_id": chat_id, "text": text})

    async def get_file_path(self, file_id: str) -> str:
        """Ask Telegram: where is this file? Returns the file_path string."""
        response = await self.client.get(f"{self.base_url}/getFile", params={"file_id": file_id})
        response.raise_for_status()

        return response.json()["result"]["file_path"]

    async def download_file(self, file_path: str, file_name: str) -> str:
        """Download the file from Telegram servers and save it locally."""
        download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        response = await self.client.get(download_url)
        response.raise_for_status()

        local_path = os.path.join(UPLOAD_DIR, file_name)
        with open(local_path, "wb") as f:
            f.write(response.content)

        return local_path

    async def start_polling(self, message_handler, document_handler, photo_handler, voice_handler):
        offset = 0
        while True:
            try:
                response = await self.client.get(f"{self.base_url}/getUpdates", 
                                                params={"offset": offset, "timeout": 20})
                updates = response.json().get("result", [])

                for update in updates:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        message = update["message"]
                        chat_id = update["message"]["chat"]["id"]
                        
                        if "document" in message:
                            # User sent a file
                            await document_handler(chat_id, message["document"])
                        elif "photo" in message:
                            await photo_handler(chat_id, message["photo"], message.get("caption",""))
                        elif "voice" in message:
                            await voice_handler(chat_id, message["voice"])
                        elif "text" in message:
                            # User sent text
                            await message_handler(chat_id, message["text"])
            except Exception as e:
                print(f"Polling error: {e}")

            await asyncio.sleep(2)
    
    async def send_document(self, chat_id: int, file_path: str):
        """Send a file back to the user."""
        with open(file_path, "rb") as f:
            files = {"document": f}
            await self.client.post(f"{self.base_url}/sendDocument", 
                    data={"chat_id":chat_id}, 
                    files=files
                    )

    async def send_chat_action(self, chat_id: int, action: str = "typing"):
        """Show a 'typing...' or 'upload_document...' indicator in Telegram."""
        await self.client.post(f"{self.base_url}/sendChatAction",
                            json={"chat_id": chat_id, "action": action})

    async def send_voice(self, chat_id: int, file_path: str):
        """Send a Voice Note (.mp3/.ogg) back to the user."""
        with open(file_path, "rb") as f:
            files = {"voice": f}
            await self.client.post(
                f"{self.base_url}/sendVoice",
                data={"chat_id": chat_id},
                files=files
            )