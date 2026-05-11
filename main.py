from fastapi import FastAPI, Request
from config import settings
import asyncio
from services.telegram import TelegramService
from services.agent import AgentService
from database.db import create_db_and_tables
from utils.document import process_pdf

app = FastAPI(title="Telegram AI Agent")
telegram_service = TelegramService()
agent_service = AgentService()

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
            "💬 **Chat**: Or we can just chat normally!\n\n"
            "How can I help you today?"
        )
        await telegram_service.send_message(chat_id, welcome_msg)
        return
        
    await telegram_service.send_chat_action(chat_id, action="typing")
    
    response = await agent_service.handle_message(chat_id, text)

    if response.startswith("__SEND_FILE__:"):
        file_path = response.replace("__SEND_FILE__:", "")
        await telegram_service.send_chat_action(chat_id, action="upload_document")
        await telegram_service.send_document(chat_id, file_path)
    else:
        await telegram_service.send_message(chat_id, response)

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
        await process_pdf(local_path, doc_id=f"{chat_id}_{file_name}")

        from repositories.sql_repo import SQLRepository
        sql_repo = SQLRepository()

        sql_repo.save_document(chat_id, file_name, local_path)

        await telegram_service.send_message(chat_id, f"✅ '{file_name}' processed and saved! You can now ask questions about it.")
    except Exception as e:
        print(f"Error processing document: {e}")
        await telegram_service.send_message(chat_id, f"❌ Error processing file: {e}")

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()

    if settings.bot_mode == "webhook":
        await telegram_service.set_webhook(settings.webhook_url)
        print(f"Webhook set to {settings.webhook_url}")
    elif settings.bot_mode == "polling":
        await telegram_service.delete_webhook()

        asyncio.create_task(telegram_service.start_polling(handle_user_message, handle_document_upload))
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