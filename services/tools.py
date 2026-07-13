from repositories.sql_repo import SQLRepository
from repositories.vector_repo import VectorRepository
from services.llm import LLMService
from ddgs import DDGS

sql_repo = SQLRepository()
vector_repo = VectorRepository()

async def save_fact(chat_id: int, fact: str) -> str:
    sql_repo.save_fact(chat_id, fact)
    return f"Successfully saved fact: {fact}"

async def search_documents(query: str, chat_id: int = None) -> str:
    if not chat_id:
        return "Error: chat_id is missing."

    llm = LLMService()
    query_emb = await llm.get_embedding(query)
    results = vector_repo.search(query_emb, chat_id=chat_id)

    if not results:
        return "No relevant document found."

    # Format the results including the page numbers
    formatted_results = []
    for r in results:
        formatted_results.append(f"[Page {r['page']}]: {r['text']}")

    return "Found information:\n" + "\n---\n".join(formatted_results)

async def list_documents(chat_id: int) -> str:
    docs = sql_repo.get_documents(chat_id)
    if not docs:
        return "You have no uploaded documents."
    
    doc_list = "\n".join(f"-{d.file_name}" for d in docs)
    return f"Your documents:\n{doc_list}"

async def send_document(file_name: str, chat_id: int) -> str:
    # Try exact match first
    doc = sql_repo.get_document_by_name(chat_id, file_name)

    # If not found, try case-insensitive partial match
    if not doc:
        all_docs = sql_repo.get_documents(chat_id)
        for d in all_docs:
            if file_name.lower() in d.file_name.lower():
                doc = d
                break

    if not doc:
        available = sql_repo.get_documents(chat_id)
        names = ",".join(d.file_name for d in available)
        return f"Document '{file_name}' not found. Available: {names}"

    return f"__SEND_FILE__:{doc.local_path}"

async def web_search(query: str, chat_id: int = None) -> str:
    """Search the live internet for current information."""
    try:
        results = []
        with DDGS() as ddgs:
            # 1. Try Text Results
            try:
                for r in ddgs.text(query, max_results=3):
                    results.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nLink: {r.get('href')}\n")
            except Exception as e:
                if "Ratelimit" in str(e):
                    results.append(f"[Error] Search engine rate limit hit for text search.")
                else:
                    results.append(f"[Error] Text search failed: {e}")
            
            # 2. Try News Results (crucial for sports, current events)
            try:
                for r in ddgs.news(query, max_results=3):
                    results.append(f"[NEWS] Title: {r.get('title')}\nSnippet: {r.get('body')}\nDate: {r.get('date')}\n")
            except Exception as e:
                if "Ratelimit" in str(e):
                    results.append(f"[Error] Search engine rate limit hit for news search.")
                else:
                    pass # Ignore other news errors if text worked

            if not results or all("[Error]" in r for r in results):
                return (
                    f"No results found on the web for query: '{query}'.\n"
                    "TIP: Try a broader query (e.g., remove specific dates or add 'score' or 'result')."
                )

            return "Web Search Results:\n" + "\n".join(results)
    except Exception as e:
        return f"Error connecting to search service: {e}"
    
# A registry mapping tool names to functions
AVAILABLE_TOOLS = {
    "save_fact": save_fact,
    "search_documents": search_documents,
    "list_documents": list_documents,
    "send_document": send_document,
    "web_search": web_search
}
