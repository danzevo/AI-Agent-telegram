import fitz # PyMuPDF
from repositories.vector_repo import VectorRepository
from services.llm import LLMService

vector_repo = VectorRepository()
llm = LLMService()

async def process_pdf(file_path: str, doc_id: str, chat_id: int):
    """Call this function when the user uploads a PDF document"""
    doc = fitz.open(file_path)
    # text = ""
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()

        chunk_size = 500
        overlap = 100

        i = 0
        chunk_idx = 0
        while i< len(text):
            chunk = text[i:i + chunk_size].strip()

            if len(chunk) > 10:
                emb = await llm.get_embedding(chunk)

                vector_repo.add_document_chunk(
                    doc_id=doc_id,
                    chunk_id=f"p{page_num}_{chunk_idx}",
                    text=chunk,
                    embedding=emb,
                    metadata={"source":file_path, "chat_id": chat_id, "page": page_num}
                )
                chunk_idx += 1
        
            i += (chunk_size - overlap)
