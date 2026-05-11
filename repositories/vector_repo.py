from database.vector_db import collection

class VectorRepository:
    def add_document_chunk(self, doc_id: str, chunk_id: str, text: str, embedding: list[float], metadata: dict):
        collection.add(
            ids=[f"{doc_id}_{chunk_id}"],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def search(self, query_embedding: list[float], n_results: int = 3) -> list[str]:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        # return the list of matching chunks
        if results["documents"] and len(results["documents"]) > 0:
            return results["documents"][0]

        return []