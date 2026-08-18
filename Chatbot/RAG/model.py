import argparse
import json
import sys
from pathlib import Path

from fastembed import TextEmbedding
import chromadb

# ---- EDIT THIS: path to the chunks.json file produced by save_chunks() ----
# Resolved relative to THIS FILE's location (not the terminal's cwd), so it
# works no matter which directory you run `python model.py` from.
SCRIPT_DIR = Path(__file__).resolve().parent
CHUNKS_PATH = str(SCRIPT_DIR / ".." / "Data" / "chunks.json")
COLLECTION_NAME = "T2Dcare"
PERSIST_PATH = str(SCRIPT_DIR / "chroma_db")
MODEL_NAME = "BAAI/bge-small-en-v1.5"
BATCH_SIZE = 64
# -----------------------------------------------------------------------


def load_chunks(chunks_path: str) -> list[dict]:
    path = Path(chunks_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {chunks_path}\n"
            f"-> Run your chunking script first (chunk_by_sentences -> "
            f"enrich_chunks_with_summary -> save_chunks) to create it, "
            f"or update CHUNKS_PATH at the top of model.py."
        )

    with open(path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Chunks file must contain a non-empty JSON list.")

    return chunks


def build_metadata(chunk: dict) -> dict:
    meta = chunk.get("metadata", {})
    return {
        "page": meta.get("page") if meta.get("page") is not None else -1,
        "sentence_count": meta.get("sentence_count", -1),
        "start_sentence": meta.get("start_sentence", -1),
        "end_sentence": meta.get("end_sentence", -1),
        "total_sentences": meta.get("total_sentences", -1),
        "sentences_per_chunk": meta.get("sentences_per_chunk", -1),
        "overlap_sentences": meta.get("overlap_sentences", -1),
        "question": meta.get("question", "") or "",
        "main_points": "; ".join(meta.get("main_points") or []),
    }


def create_and_store_embeddings(
    chunks: list[dict],
    collection_name: str = "T2Dcare",
    persist_path: str = "./chroma_db",
    model_name: str = "BAAI/bge-small-en-v1.5",
    batch_size: int = 64,
):
    texts, metadatas, ids = [], [], []

    for i, c in enumerate(chunks):
        try:
            texts.append(c["text"])
            metadatas.append(build_metadata(c))
            ids.append(f"chunk_{c['chunk_id']}")
        except KeyError as e:
            print(f"[skip] chunk index {i} missing key {e}, skipping.", file=sys.stderr)

    if not texts:
        raise ValueError("No valid chunks to embed after validation.")

    print(f"Loading embedding model: {model_name}")
    embedding_model = TextEmbedding(model_name=model_name)

    embeddings = []
    total = len(texts)
    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = list(embedding_model.embed(batch))
        embeddings.extend(e.tolist() for e in batch_embeddings)
        print(f"  embedded {min(i + batch_size, total)}/{total}")

    chroma_client = chromadb.PersistentClient(path=persist_path)
    collection = chroma_client.get_or_create_collection(name=collection_name)

    # upsert instead of add -> safe to re-run without duplicate-id errors
    collection.upsert(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    print(f"Embeddings stored successfully! ({len(texts)} chunks) -> "
          f"collection='{collection_name}' path='{persist_path}'")
    return collection


def main():
    # All args are OPTIONAL now — if you don't pass any flags, the constants
    # at the top of this file (CHUNKS_PATH, COLLECTION_NAME, etc.) are used.
    parser = argparse.ArgumentParser(description="Embed and store guideline chunks in Chroma.")
    parser.add_argument("--chunks", default=CHUNKS_PATH, help="Path to chunks JSON file")
    parser.add_argument("--collection", default=COLLECTION_NAME, help="Chroma collection name")
    parser.add_argument("--persist", default=PERSIST_PATH, help="Chroma persist directory")
    parser.add_argument("--model", default=MODEL_NAME, help="fastembed model name")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    print(f"Loaded {len(chunks)} chunks from {args.chunks}")

    create_and_store_embeddings(
        chunks=chunks,
        collection_name=args.collection,
        persist_path=args.persist,
        model_name=args.model,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()