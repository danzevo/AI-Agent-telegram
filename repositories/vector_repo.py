from database.vector_db import collection

class VectorRepository:
    def add_document_chunk(self, doc_id: str, chunk_id: str, text: str, embedding: list[float], metadata: dict):
        collection.add(
            ids=[f"{doc_id}_{chunk_id}"],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def search(self, query_embedding: list[float], chat_id: int, n_results: int = 3) -> list[dict]:
        results = collection.query(
            query_embeddings=[query_embedding],
            where={"chat_id": chat_id},
            n_results=n_results
        )

        output = []
        if results["documents"] and len(results["documents"]) > 0:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else []

            for doc, meta in zip(documents, metadatas):
                output.append({
                    "text": doc,
                    "page": meta.get("page", "unknown")
                })

        return output