import chromadb

# Creates a local folder "chroma_data" in the project root
chroma_client = chromadb.PersistentClient(path="./chroma_data")
collection = chroma_client.get_or_create_collection(name="user_documents")