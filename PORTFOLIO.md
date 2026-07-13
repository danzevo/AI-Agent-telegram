# 🤖 Autonomous Telegram AI Agent: Multimodal Dual-Memory Assistant
*(Role: AI Engineer & Backend Developer)*

## 📸 System Interface
`[ ➔ INSERT SCREENSHOT HERE ]`  
*(Tip: Take a screenshot of your Telegram bot answering a complex question from an uploaded PDF, describing an image, or showing its "Web Research" in action!)*

---

## 💡 The Problem
Large Language Models (LLMs) are incredibly smart, but they suffer from "amnesia"—they cannot natively remember past conversations, user facts, or search local files. Furthermore, interacting with enterprise data through standard ChatGPT risks exposing sensitive information. Employees need a localized, accessible, and intelligent assistant that actually remembers who they are, what documents they own, and can process multi-format inputs like images.

## 🎯 The Solution
I engineered an autonomous **Multimodal Knowledge Assistant** accessible directly via a Telegram Bot. By utilizing a custom-built ReAct (Reasoning and Acting) loop, the agent autonomously dictates when to save relational facts to a SQLite database, when to perform live web research, when to extract and embed PDF documents into a ChromaDB Vector Database, and how to analyze images. It runs 100% locally using LM Studio, ensuring absolute data privacy.

---

## 🎓 What I've Learned (Skills Acquired)
Through building this project and expanding upon my other projects in Python, I have developed deep expertise in several cutting-edge AI domains:

* **Natural Language Processing (NLP):** Mastered prompting techniques, context-window management, and orchestrating complex LLM responses. I've moved beyond simple chatbots to building deterministic JSON outputs (Function/Tool Calling).
* **Multimodal AI:** Successfully integrated Vision-Language Models (VLMs) like Qwen2.5-VL and Llama 3.2 Vision. I learned how to encode images (Base64) and structure multimodal API payloads so the AI can "see" and describe photos sent by users.
* **RAG (Retrieval-Augmented Generation):** Built a complete RAG pipeline from scratch without relying on heavy frameworks. I learned how to extract text from PDFs (PyMuPDF), chunk the data, generate semantic embeddings, and store/query them using a Vector Database (ChromaDB) to ground the AI's answers in real facts.
* **Autonomous AI Agents:** Designed a custom ReAct (Reasoning and Acting) loop. Instead of hardcoding logic, I taught the LLM to autonomously decide *when* to search the web, *when* to query the database, and *when* to just chat normally.

---

## 🛠️ The Tech Stack
* **AI / ML:** Qwen2.5-VL / Llama 3.2 Vision (Multimodal), LM Studio, Nomic Embeddings (`nomic-embed-text-v1.5`)
* **Core Backend:** Python, FastAPI, Asyncio
* **Databases:** SQLite (SQLModel) for relational data & chat history, ChromaDB for Vector RAG
* **Integrations:** Telegram Bot API (Async Polling & Webhooks), PyMuPDF (fitz), DuckDuckGo Search API

---

## 🏗️ Engineering & Architecture Highlights

### 1. Custom ReAct Tool-Calling Loop
Rather than relying on heavy, black-box frameworks like LangChain, I built the agent's "brain" from scratch. The LLM is strictly prompted to output formatted JSON to trigger backend tool executions (`save_fact`, `web_search`, `search_documents`, `list_documents`, `send_document`). The loop intercepts these JSON payloads, securely executes the Python function, and iteratively feeds the result back to the LLM to generate a natural, conversational response.

### 2. Live Web Research (Autonomous Intelligence)
I "leveled up" the agent from a static document reader to a live researcher. By integrating a Web Search tool, the agent can autonomously decide when its internal knowledge is insufficient and perform a live query on the internet. This allows it to bridge the gap between "trained knowledge" and "real-time events" like sports results, weather, or current market news.

### 3. Dual-Memory Architecture
Most AI applications only feature one type of memory. I engineered a dual-memory system:
* **Relational Memory:** Uses SQLite to store explicit user facts (e.g., names, job titles, preferences) and **persistent chat history**. This ensures context is maintained even after server restarts.
* **Semantic Memory (RAG):** Uses ChromaDB to process and embed uploaded PDFs. When a user queries their documents, the RAG pipeline dynamically fetches the most relevant chunks of text to provide highly accurate, hallucination-free answers.

### 4. Asynchronous Execution & Firewall Bypassing
To ensure rapid response times and the ability to handle large PDF processing simultaneously with chat messages, the entire backend is fully asynchronous using `httpx` and `asyncio`. Additionally, to accommodate restrictive corporate environments that intercept SSL certificates, I built a configurable SSL-verification bypass natively into the Telegram polling client.

---

## 🔗 Links
* **[GitHub Repository]** -> `https://github.com/danzevo/AI-Agent-telegram.git`
