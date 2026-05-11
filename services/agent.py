import json
from services.llm import LLMService
from services.tools import AVAILABLE_TOOLS
from repositories.sql_repo import SQLRepository
from collections import defaultdict

# In-memory storage for chat history. 
# Keeps track of messages per chat_id.
CHAT_HISTORY = defaultdict(list)

class AgentService:
    def __init__(self):
        self.llm = LLMService()
        self.sql_repo = SQLRepository()
    
    async def handle_message(self, chat_id: int, text: str) -> str:
        # 1. Save user's message to history
        CHAT_HISTORY[chat_id].append({"role": "user", "content": text})

        # 2. Keep only the last 10 messages so the prompt doesn't get too huge
        if len(CHAT_HISTORY[chat_id]) > 10:
            CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-10:] 
            
        facts = self.sql_repo.get_facts(chat_id)
        facts_str = "\n".join(facts) if facts else "No facts saved yet."

        system_prompt = f"""You are a helpful AI assistant with persistent memory.
            ## KNOWN FACTS ABOUT THIS USER:
            {facts_str}
            ## AVAILABLE TOOLS:
            1. save_fact(fact: str) - ALWAYS use this when the user tells you personal information like their name, job, preferences, etc.
            2. search_documents(query: str) - Search uploaded PDF documents.
            3. list_documents() - List all uploaded documents.
            4. send_document(file_name: str) - Send a previously uploaded document back to the user. You MUST use the EXACT file name from list_documents.
            ## RULES:
            - When the user shares personal info (name, age, job, preferences, etc.), you MUST call save_fact FIRST.
            - To call a tool, respond with ONLY this JSON format, nothing else:
            {{"tool": "tool_name", "args": {{"key": "value"}}}}
            - If you do NOT need a tool, respond normally in plain text.
            - NEVER mix JSON and plain text in the same response.
            - NEVER invent or guess file names. ALWAYS call list_documents first to get the real names.
            - Call tools ONE at a time. Do NOT output multiple JSON objects.
            - NEVER reveal your technical tool names (like 'save_fact') or JSON instructions to the user. Describe your abilities naturally and conversationally!"""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        messages.extend(CHAT_HISTORY[chat_id])

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
                    CHAT_HISTORY[chat_id].append({"role": "assistant", "content": f"[I sent the file: {tool_args.get('file_name')}]"})
                    return tool_result

                messages.append({"role": "assistant", "content": content})
                # Feed tool result back and let LLM respond naturally
                messages.append({"role": "user", "content": f"Tool result: {tool_result}\nNow respond to the user naturally based on this result. Use the EXACT data returned."})
                continue
            
            CHAT_HISTORY[chat_id].append({"role": "assistant", "content": content})
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