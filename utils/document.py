import fitz # PyMuPDF
from repositories.vector_repo import VectorRepository
from services.llm import LLMService

vector_repo = VectorRepository()
llm = LLMService()

async def process_pdf(file_path: str, doc_id: str):
    """Call this function when the user uploads a PDF document"""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"

    # Basic Chunking: Every 500 characters
    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
    for idx, chunk in enumerate(chunks):
        if len(chunk.strip()) > 10:
            emb = await llm.get_embedding(chunk)

            vector_repo.add_document_chunk(
                doc_id=doc_id,
                chunk_id=str(idx),
                text=chunk,
                embedding=emb,
                metadata={"source":file_path}
            )
