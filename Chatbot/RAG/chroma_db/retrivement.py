"""
Query the Chroma collection built by model.py.

Run directly for a quick manual test:
    python retrieve.py

Or import query_chunks() into your chatbot/main.py.
"""

from pathlib import Path

from fastembed import TextEmbedding
import chromadb

SCRIPT_DIR = Path(__file__).resolve().parent
PERSIST_PATH = str(SCRIPT_DIR / "chroma_db")
COLLECTION_NAME = "T2Dcare"
MODEL_NAME = "BAAI/bge-small-en-v1.5"  # must match the model used in model.py


def query_chunks(question: str, top_k: int = 5, persist_path: str = PERSIST_PATH,
                  collection_name: str = COLLECTION_NAME, model_name: str = MODEL_NAME):
    """
    Embed `question` and return the top_k most relevant chunks from Chroma.

    Returns a list of dicts: [{"text": ..., "metadata": {...}, "distance": ...}, ...]
    sorted by relevance (closest first).
    """
    embedding_model = TextEmbedding(model_name=model_name)
    query_embedding = list(embedding_model.embed([question]))[0].tolist()

    chroma_client = chromadb.PersistentClient(path=persist_path)
    collection = chroma_client.get_collection(name=collection_name)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    hits = []
    for text, meta, dist, doc_id in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0],
    ):
        hits.append({"id": doc_id, "text": text, "metadata": meta, "distance": dist})

    return hits


def print_results(hits):
    for i, h in enumerate(hits, 1):
        page = h["metadata"].get("page", "?")
        print(f"\n--- Result {i} (id={h['id']}, page={page}, distance={h['distance']:.4f}) ---")
        print(h["text"])


if __name__ == "__main__":
    question = input("Ask a question: ").strip()
    hits = query_chunks(question, top_k=5)
    print_results(hits)