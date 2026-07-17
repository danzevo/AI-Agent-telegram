import os
import httpx
from config import settings

if not settings.ssl_verify:
    # --- 🚨 SLEDGEHAMMER SSL BYPASS 🚨 ---
    os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
    os.environ["HF_HUB_DISABLE_XET"] = "1"

    # Monkey-patch httpx to forcefully disable SSL verification globally
    _original_client_init = httpx.Client.__init__
    def _patched_client_init(self, *args, **kwargs):
        kwargs["verify"] = False
        _original_client_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_client_init
    # -------------------------------------

from fastapi import FastAPI, Request
from config import settings
import asyncio
from services.telegram import TelegramService
from services.agent import AgentService
from database.db import create_db_and_tables
from utils.document import process_pdf
import base64
from faster_whisper import WhisperModel
import edge_tts

app = FastAPI(title="Telegram AI Agent")
telegram_service = TelegramService()
agent_service = AgentService()
whisper_model = WhisperModel("base", device="cpu", compute_type="int8", download_root="./whisper-model")

async def handle_user_message(chat_id: int, text:str):
    # Optional: Send "Thinking..." indicator
    # await telegram_service.send_message(chat_id, "Thinking...")
    print(f"Received message : {text}")
    if text.strip() == "/start":
        welcome_msg = (
            "Hello! 👋 I am your Personal AI Assistant.\n\n"
            "Here is what I can do for you:\n"
            "🧠 **Remember details**: I can learn and store facts about you.\n"
            "📄 **Manage PDFs**: You can upload PDF documents for me to read.\n"
            "🔎 **Search & Retrieve**: You can ask me questions about your documents, or ask me to send them back to you.\n"
            "🌐 **Web Search**: You can ask me about current events, news, or weather, and I will search the live internet!\n"
            "💬 **Chat**: Or we can just chat normally!\n\n"
            "How can I help you today?"
        )
        await telegram_service.send_message(chat_id, welcome_msg)
        return

    # Start the recurring typing indicator task
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(chat_id, stop_typing))

    try:
        # Get response from the AI Agent (which might take a while if it searches the web)
    # await telegram_service.send_chat_action(chat_id, action="typing")
    
        response = await agent_service.handle_message(chat_id, text)

        if response.startswith("__SEND_FILE__:"):
            file_path = response.replace("__SEND_FILE__:", "")
            await telegram_service.send_chat_action(chat_id, action="upload_document")
            await telegram_service.send_document(chat_id, file_path)
        else:
            await telegram_service.send_message(chat_id, response)
    finally:
        # Ensure typing indicator is stopped and task is cleaned up
        stop_typing.set()
        await typing_task
        
async def handle_document_upload(chat_id: int, document: dict):
    """Handle when user sends a file (PDF) to the bot."""
    file_name = document.get("file_name", "unknown")
    file_id = document["file_id"]

    # Only process PDFs
    if not file_name.lower().endswith(".pdf"):
        await telegram_service.send_message(chat_id, "Sorry, I only support PDF files for now.")
        return

    await telegram_service.send_message(chat_id, f"📄 Received '{file_name}'. Processing...")
    try:
        # Step 1: Get file path from Telegram
        file_path = await telegram_service.get_file_path(file_id)
        # Step 2: Download file locally
        local_path = await telegram_service.download_file(file_path, file_name)
        # Step 3: Extract text, chunk, embed, store in ChromaDB
        await process_pdf(local_path, doc_id=f"{chat_id}_{file_name}", chat_id=chat_id)

        from repositories.sql_repo import SQLRepository
        sql_repo = SQLRepository()

        sql_repo.save_document(chat_id, file_name, local_path)

        await telegram_service.send_message(chat_id, f"✅ '{file_name}' processed and saved! You can now ask questions about it.")
    except Exception as e:
        print(f"Error processing document: {e}")
        await telegram_service.send_message(chat_id, f"❌ Error processing file: {e}")

async def handle_photo_upload(chat_id: int, photos: list, caption: str):
    await telegram_service.send_message(chat_id, "🖼️ Analyzing image...")
    # Telegram sends multiple sizes. Grab the last one (highest resolution)
    file_id = photos[-1]["file_id"]
    try:
        file_path = await telegram_service.get_file_path(file_id)
        local_path = await telegram_service.download_file(file_path, "temp_image.jpg")

        # Encode image to Base64
        with open(local_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

        # Send to Qwen2.5-VL via AgentService
        response = await agent_service.handle_message(chat_id, caption, image_base64=image_base64)
        await telegram_service.send_message(chat_id, response)
    except Exception as e:
        await telegram_service.send_message(chat_id, f"❌ Error processing image: {e}")

async def handle_voice_upload(chat_id: int, voice: dict):
    await telegram_service.send_message(chat_id, "🎤 Listening...")
    file_id = voice["file_id"]
    try:
        file_path = await telegram_service.get_file_path(file_id)
        local_path = await telegram_service.download_file(file_path, "temp_voice.ogg")

        # Transcribe audio to text locally
        segments, _ = whisper_model.transcribe(local_path, beam_size=5)
        text = "".join([segment.text for segment in segments]).strip()

        # 2. Send transcribed text to the LLM (Qwen/Llama)
        response = await agent_service.handle_message(chat_id, text)

        # 3. Show "recording voice..." indicator in Telegram
        await telegram_service.send_chat_action(chat_id, action="record_voice")

        # 4. Generate Audio using edge-tts (Default Female Voice: en-US-AriaNeural)
        output_audio_path = f"./uploads/reply_{chat_id}.mp3"
        communicate = edge_tts.Communicate(response, "en-US-AriaNeural")
        await communicate.save(output_audio_path)

        # 5. Send the audio back to the user
        await telegram_service.send_voice(chat_id, output_audio_path)

        # 6. Clean up the audio file so we don't waste disk space
        if os.path.exists(output_audio_path):
            os.remove(output_audio_path)
    except Exception as e:
        await telegram_service.send_message(chat_id, f"❌ Error processing voice: {e}")


async def keep_typing(chat_id: int, stop_event: asyncio.Event):
    """Refreshes the 'typing...' status every 4.5 seconds until stopped."""
    while not stop_event.is_set():
        await telegram_service.send_chat_action(chat_id, action="typing")
        try:
            # Wait for the stop event OR timeout after 4.5 seconds
            await asyncio.wait_for(stop_event.wait(), timeout=4.5)
        except asyncio.TimeoutError:
            continue # Timeout reached, repeat the loop to send typing again
        except Exception as e:
            print(f"Typing indicator error: {e}")
            break

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()

    if settings.bot_mode == "webhook":
        await telegram_service.set_webhook(settings.webhook_url)
        print(f"Webhook set to {settings.webhook_url}")
    elif settings.bot_mode == "polling":
        await telegram_service.delete_webhook()

        asyncio.create_task(telegram_service.start_polling(handle_user_message, handle_document_upload, handle_photo_upload, handle_voice_upload))
        print("Started polling...")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    if settings.bot_mode != "webhook":
        return {"status": "ignored"}

    update = await request.json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        message = update["message"]

        if "document" in message:
            asyncio.create_task(handle_document_upload(chat_id, message["document"]))
        elif "text" in message:
            print(f"Received message : {message["text"]}")
            asyncio.create_task(handle_user_message(chat_id, message["text"]))

    return {"status": "ok"}