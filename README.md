# Multimodal Knowledge Assistant (Telegram AI Agent)

A privacy-focused, autonomous Telegram AI Agent built with FastAPI and a local Vision-Language Model (Qwen2.5-VL / Llama 3.2 Vision) via LM Studio. This agent features relational memory for user facts, semantic memory for PDF document retrieval (RAG), multimodal image analysis, and is orchestrated using a custom ReAct tool-calling loop.

## Features
* **Conversational AI**: Powered by advanced LLMs (Qwen2.5 / Llama 3).
* **Multimodal Image Analysis**: Can process, "see", and describe images sent directly in Telegram chat using Vision-Language Models (VLMs).
* **Autonomous Tool Calling**: Built-in ReAct loop allows the agent to autonomously decide when to use tools (search web, search PDF, save facts) without relying on heavy frameworks.
* **Persistent Memory**: Learns and remembers user facts using SQLite & SQLModel.
* **Live Web Research**: Uses DuckDuckGo to research current events, news, and weather in real-time.
* **Chat History Persistence**: Conversation history is stored in SQLite, allowing the bot to remember context across restarts.
* **Document Management**: Users can upload PDFs directly via Telegram.
* **Semantic Search (RAG)**: Extracts, chunks, and embeds PDFs into ChromaDB for context-aware Q&A.
* **File Retrieval**: Can list and send previously uploaded documents back to the user.
* **Async Polling & Webhooks**: Supports both local polling (great for corporate firewalls) and production webhooks.

## Architecture
* **Framework**: FastAPI (Async)
* **Database**: SQLite (SQLModel) & ChromaDB (Vector DB for RAG)
* **LLM**: LM Studio (Qwen2.5-VL/Llama Vision + nomic-embed-text-v1.5)
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
   LLM_MODEL="qwen2.5-vl-7b-instruct"
   BOT_MODE="polling"
   WEBHOOK_URL="https://your-ngrok-url.app/webhook"
   SSL_VERIFY=False
   ```

4. **Run the Bot**
   ```bash
   uvicorn main:app --reload
   ```
