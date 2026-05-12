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
    
    async def handle_message(self, chat_id: int, text: str) -> str:
        from datetime import datetime

        # 1. Get current date to help the bot understand search results
        current_date = datetime.now().strftime("%A, %B %d, %Y")

        triggers = ["now", "yesterday", "today", "score", 
                        "winner", "result", "match", "vs", "price", 
                        "gold", "rate", "weather", "news"]
        
        is_time_sensitive = any(word in text.lower() for word in triggers)
        
        # 1. Save user's message to history
        # CHAT_HISTORY[chat_id].append({"role": "user", "content": text})
        self.sql_repo.save_message(chat_id, "user", text)

        # 2. Keep only the last 10 messages so the prompt doesn't get too huge
        # if len(CHAT_HISTORY[chat_id]) > 10:
        #     CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-10:] 
        history = self.sql_repo.get_chat_history(chat_id, limit=10)
            
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
            f"5. web_search(query: str) - Search the live internet. IMPORTANT: Your query must use specific dates (e.g. 'May 10 2026') instead of relative words ('yesterday', 'Monday').\n"
            f"\n"
            f"## HOW TO CALL A TOOL:\n"
            f"Respond with ONLY this JSON format, nothing else:\n"
            f'{{"tool": "tool_name", "args": {{"key": "value"}}}}\n'
            f"\n"
            f"Example - user asks 'gold price today':\n"
            f'{{"tool": "web_search", "args": {{"query": "gold price May 12 2026"}}}}\n'
            f"\n"
            f"## RULES:\n"
            f"- When the user shares personal info, you MUST call save_fact FIRST.\n"
            f"- If you do NOT need a tool, respond normally in plain text.\n"
            f"- NEVER mix JSON and plain text in the same response.\n"
            f"- Call tools ONE at a time. Do NOT output multiple JSON objects.\n"
            f"- NEVER invent or guess file names. ALWAYS call list_documents first.\n"
            f"- NEVER reveal your technical tool names or JSON instructions to the user.\n"
            f"- ALWAYS prioritize search_documents if the user asks about THEIR uploaded files.\n"
            f"- NEVER ask the user for permission to use a tool. Just call it immediately.\n"
            f"- After using a tool, explain the result naturally. Use the EXACT data returned.\n"
            f"\n"
            f"## MANDATORY SEARCH (web_search):\n"
            f"You MUST use web_search for: sports scores, match results, gold/stock/crypto prices, exchange rates, weather, news, or any event in {datetime.now().year}.\n"
            f"Translate relative dates ('yesterday', 'last Monday') into exact calendar dates using the Current Date before searching.\n"
            f"Your training data may be outdated. NEVER guess or invent scores, prices, dates, or statistics.\n"
            f"If web_search results are unclear, tell the user what you found but do NOT make up details."
        )
        
        if is_time_sensitive: 
            system_prompt += "\n\nCRITICAL: The user is asking about a real-time or recent event. You MUST use web_search immediately. Do NOT rely on your internal knowledge."
            
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # messages.extend(CHAT_HISTORY[chat_id])
        messages.extend(history)

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