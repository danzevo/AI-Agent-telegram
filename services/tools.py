from repositories.sql_repo import SQLRepository
from repositories.vector_repo import VectorRepository
from services.llm import LLMService

sql_repo = SQLRepository()
vector_repo = VectorRepository()

async def save_fact(chat_id: int, fact: str) -> str:
    sql_repo.save_fact(chat_id, fact)
    return f"Successfully saved fact: {fact}"

async def search_documents(query: str, chat_id: int = None) -> str:
    llm = LLMService()
    query_emb = await llm.get_embedding(query)
    results = vector_repo.search(query_emb)

    if not results:
        return "No relevant document found."

    return "Found information:\n" + "\n".join(results)

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

# A registry mapping tool names to functions
AVAILABLE_TOOLS = {
    "save_fact": save_fact,
    "search_documents": search_documents,
    "list_documents": list_documents,
    "send_document": send_document,
}
