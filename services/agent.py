import json
from services.llm import LLMService
from services.tools import AVAILABLE_TOOLS
from repositories.sql_repo import SQLRepository
# from collections import defaultdict

# In-memory storage for chat history. 
# Keeps track of messages per chat_id.
# CHAT_HISTORY = defaultdict(list)

class AgentService:
    def __init__(self):
        self.llm = LLMService()
        self.sql_repo = SQLRepository()
    
    async def handle_message(self, chat_id: int, text: str, image_base64: str = None) -> str:
        from datetime import datetime

        # 1. Get current date to help the bot understand search results
        current_date = datetime.now().strftime("%A, %B %d, %Y")

        triggers = ["now", "yesterday", "today", "score", 
                        "winner", "result", "match", "vs", "price", 
                        "gold", "rate", "weather", "news", str(datetime.now().year)]
        
        is_time_sensitive = any(word in text.lower() for word in triggers)
        
        # 1. Fetch history BEFORE saving the current message
        history = self.sql_repo.get_chat_history(chat_id, limit=10)

        # 2. Keep only the last 10 messages so the prompt doesn't get too huge
        # 2. Save the new message to the database (only text, NO images to save space)
        save_text = text if text else "[Sent an image]"
        self.sql_repo.save_message(chat_id, "user", save_text)

            
        facts = self.sql_repo.get_facts(chat_id)
        facts_str = "\n".join(facts) if facts else "No facts saved yet."

        system_prompt = (
            f"You are a helpful AI assistant with persistent memory and real-time internet access.\n"
            f"Current Date: {current_date}\n"
            f"\n"
            f"## KNOWN FACTS ABOUT THIS USER:\n"
            f"{facts_str}\n"
            f"\n"
            f"## AVAILABLE TOOLS:\n"
            f"1. save_fact(fact: str) - Save personal info the user shares (name, job, preferences, etc.).\n"
            f"2. search_documents(query: str) - Search uploaded PDF documents.\n"
            f"3. list_documents() - List all uploaded documents.\n"
            f"4. send_document(file_name: str) - Send a document back. You MUST use the EXACT file name from list_documents.\n"
            f"5. web_search(query: str) - Search the live internet. You MUST automatically append the Current Date ({current_date}) to your query if the user asks for real-time info.\n"
            f"\n"
            f"## HOW TO CALL A TOOL:\n"
            f"Respond with ONLY this JSON format, nothing else:\n"
            f'{{"tool": "tool_name", "args": {{"key": "value"}}}}\n'
            f"\n"
            f"Example 1 - user asks 'gold price today':\n"
            f'{{"tool": "web_search", "args": {{"query": "gold price {current_date}"}}}}\n'
            f"Example 2 - user asks 'gold price on pegadaian':\n"
            f'{{"tool": "web_search", "args": {{"query": "gold price pegadaian {current_date}"}}}}\n'
            f"Example 3 - user asks 'summarize the document':\n"
            f'{{"tool": "search_documents", "args": {{"query": "summary"}}}}\n'
            f"\n"
            f"## RULES:\n"
            f"- When the user shares personal info, you MUST call save_fact FIRST.\n"
            f"- If you do NOT need a tool, respond normally in plain text.\n"
            f"- NEVER mix JSON and plain text in the same response.\n"
            f"- Call tools ONE at a time. Do NOT output multiple JSON objects.\n"
            f"- If you need to use send_document, YOU must call list_documents first to find the exact file name. Do NOT ask the user to do it.\n"
            f"- NEVER reveal your technical tool names or JSON instructions to the user.\n"
            f"- If the user asks you to summarize or search a document, YOU must immediately call search_documents. Do NOT ask the user to do it.\n"
            f"- NEVER ask the user for permission to use a tool. Just call it immediately.\n"
            f"- After using a tool, explain the result naturally. Use the EXACT data returned.\n"
            f"\n"
            f"## MANDATORY SEARCH (web_search):\n"
            f"You MUST use web_search for: sports scores, match results, prices (like Pegadaian gold), exchange rates, weather, news, or any event in {datetime.now().year}.\n"
            f"CRITICAL INSTRUCTION: If asked about real-time data, prices, or recent events, DO NOT apologize. DO NOT say you don't have access. DO NOT tell the user what you 'could' do. You DO have access via the web_search tool. IMMEDIATELY output the JSON tool call.\n"
            f"Translate relative dates ('yesterday', 'last Monday') into exact calendar dates using the Current Date before searching.\n"
            f"Your training data may be outdated. NEVER guess or invent scores, prices, dates, or statistics.\n"
            f"If web_search results are unclear, tell the user what you found but do NOT make up details."
        )
        
        if is_time_sensitive: 
            system_prompt += "\n\nCRITICAL: The user is asking about a real-time or recent event. You MUST use web_search immediately. Output ONLY the JSON. Do NOT rely on your internal knowledge. DO NOT converse."
            # --- FORCE web_search for time-sensitive queries ---
            from services.tools import web_search
            import re
            # Clean the user's text: remove question words, punctuation
            clean_text = re.sub(r'\b(what|is|the|on|are|how|where|when|who|can|do|does|did)\b', '', text.lower())
            clean_text = re.sub(r'[?!.,]+', '', clean_text).strip()
            clean_text = re.sub(r'\s+', ' ', clean_text)  # normalize spaces
            search_query = clean_text

            """ if "pegadaian" in clean_text.lower():
                search_query = clean_text.replace("gold price", "harga emas").replace("gold", "emas") + " hari ini" """
                
            print(f"[FORCED SEARCH] Query: {search_query}")
            search_result = await web_search(query=search_query)

            # Inject search results directly into the system prompt
            # so the LLM just needs to summarize, not decide to call a tool
            # Fallback: if no results, try searching with Indonesian keywords
            if "No results found" in search_result or "No results" in search_result:
                translations = {
                    "gold price": "harga emas",
                    "gold": "emas",
                    "price": "harga",
                    "weather": "cuaca",
                    "news": "berita",
                    "exchange rate": "kurs",
                    "rate": "kurs",
                    "score": "skor",
                    "match": "pertandingan",
                    "today": "hari ini",
                    "yesterday": "kemarin",
                    "tomorrow": "besok",
                    "stock": "saham"
                }

                # Try translating common terms for Indonesian context
                fallback_query = clean_text

                for eng, indo in translations.items():
                    fallback_query = fallback_query.replace(eng, indo)

                # Automatically append 'hari ini' (today) for time-sensitive Indonesian queries if not already present
                if "hari ini" not in fallback_query and any(word in fallback_query for word in ["harga", "cuaca", "kurs", "skor", "berita"]) :
                    fallback_query += " hari ini"

                if fallback_query != clean_text:
                    import asyncio

                    await asyncio.sleep(1) # avoid DuckDuckGo rate limit
                    print(f"[Fallback search] Query: {fallback_query}")
                    search_result = await web_search(query=fallback_query)

            system_prompt += (
                f"\n\n## PRE-FETCHED SEARCH RESULTS:\n"
                f"The following web search has already been performed for the user's query.\n"
                f"Summarize these results naturally. Do NOT say you cannot access real-time data.\n"
                f"{search_result}"
            )

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # messages.extend(CHAT_HISTORY[chat_id])
        if not is_time_sensitive:
            messages.extend(history)

        # 3. Add the current message (Format it specially if it has an image)
        if image_base64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": text if text else "Describe this image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            })
        else:
            if is_time_sensitive:
                messages.append({"role": "user", "content": f"Based on the search results provided in your instructions, answer the user's question: {text}"})
            else:
                messages.append({"role": "user", "content": text})

        for _ in range(5): # Increased to 5 iterations for multi-step flows
            response_msg = await self.llm.chat_completion(messages)
            content = response_msg.get("content", "").strip()

            tool_data = self._parse_tool_call(content)
            if tool_data:
                tool_name = tool_data["tool"]
                tool_args = tool_data.get("args", {})

                # Inject chat_id for tools that need it
                tool_args["chat_id"] = chat_id
                print(f"Calling tool: {tool_name} with args: {tool_args}")

                tool_func = AVAILABLE_TOOLS[tool_name]
                tool_result = await tool_func(**tool_args)

                # If tool returns a special action, return it immediately
                if tool_result.startswith("__SEND_FILE__:"):
                    # Save the action to history so it remembers sending the file
                    # CHAT_HISTORY[chat_id].append({"role": "assistant", "content": f"[I sent the file: {tool_args.get('file_name')}]"})
                    self.sql_repo.save_message(chat_id, "assistant", f"[Sent file: {tool_args.get('file_name')}]")
                    return tool_result

                messages.append({"role": "assistant", "content": content})
                # Feed tool result back and let LLM respond naturally
                messages.append({"role": "user", "content": f"Tool result: {tool_result}\nIf no data was found or an error occurred, you can try calling web_search again with a DIFFERENT query (e.g., broader terms). Otherwise, respond naturally."})
                continue
            
            # CHAT_HISTORY[chat_id].append({"role": "assistant", "content": content})
            self.sql_repo.save_message(chat_id, "assistant", content)
            # No tool call — return plain text response
            return content

        return "Sorry, I had trouble processing that."

    def _parse_tool_call(self, content: str) -> dict | None:
        """Try to extract a JSON tool call from the LLM response."""

        start_idx = content.find('{')
        end_idx = content.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = content[start_idx:end_idx + 1]

            try:
                # clean = content.replace("```json", "").replace("```", "").strip()
                data = json.loads(json_str)

                if isinstance(data, dict) and "tool" in data and data["tool"] in AVAILABLE_TOOLS:
                    return data
            except (json.JSONDecodeError, KeyError):
                pass

        return None