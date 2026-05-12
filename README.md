# Personal Knowledge Assistant (Telegram AI Agent)

A privacy-focused, autonomous Telegram AI Agent built with FastAPI and a local LLaMA 3 8B model via LM Studio. This agent features both relational memory for user facts and semantic memory for PDF document retrieval, orchestrated using a custom ReAct tool-calling loop.

## Features
* **Conversational AI**: Powered by LLaMA 3 8B Instruct.
* **Persistent Memory**: Learns and remembers user facts using SQLite & SQLModel.
* **Live Web Research**: Uses DuckDuckGo to research current events, news, and weather in real-time.
* **Chat History Persistence**: Conversation history is stored in SQLite, allowing the bot to remember context across restarts.
* **Document Management**: Users can upload PDFs directly via Telegram.
* **Semantic Search (RAG)**: Extracts, chunks, and embeds PDFs into ChromaDB for context-aware Q&A.
* **File Retrieval**: Can list and send previously uploaded documents back to the user.
* **Async Polling & Webhooks**: Supports both local polling (great for corporate firewalls) and production webhooks.

## Architecture
* **Framework**: FastAPI (Async)
* **Database**: SQLite (SQLModel) & ChromaDB
* **LLM**: LM Studio (LLaMA 3 8B + nomic-embed-text-v1.5)
* **Pattern**: Controller -> Service -> Repository

## Setup

1. **Prerequisites**
   * Python 3.10+
   * LM Studio running locally with LLaMA 3 8B and `nomic-embed-text-v1.5`
   * A Telegram Bot Token from [@BotFather](https://t.me/botfather)

2. **Installation**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   pip install duckduckgo-search
   ```

3. **Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   TELEGRAM_BOT_TOKEN="your_token_here"
   LM_STUDIO_URL="http://localhost:1234/v1"
   BOT_MODE="polling"
   WEBHOOK_URL="https://your-ngrok-url.app/webhook"
   SSL_VERIFY=False
   ```

4. **Run the Bot**
   ```bash
   uvicorn main:app --reload
   ```
