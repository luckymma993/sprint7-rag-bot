import json
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
KB_DIR = ROOT / "knowledge_base"
INDEX_DIR = ROOT / "index"
INDEX_FILE = INDEX_DIR / "faiss.index"
CHUNKS_FILE = INDEX_DIR / "chunks.jsonl"
INFO_FILE = INDEX_DIR / "index_info.json"

MODEL_NAME = "intfloat/multilingual-e5-base"
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "


def load_model():
    return SentenceTransformer(MODEL_NAME, device="cpu")


def load_chunks():
    with CHUNKS_FILE.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file]


def load_chunks_from(path):
    with Path(path).open(encoding="utf-8") as file:
        return [json.loads(line) for line in file]


class Searcher:
    def __init__(self, index_dir=INDEX_DIR):
        index_dir = Path(index_dir)
        self.model = load_model()
        self.index = faiss.read_index(str(index_dir / "faiss.index"))
        self.chunks = load_chunks_from(index_dir / "chunks.jsonl")

    def search(self, query, k=3):
        vector = self.model.encode(
            [QUERY_PREFIX + query], normalize_embeddings=True, convert_to_numpy=True
        ).astype(np.float32)
        scores, ids = self.index.search(vector, k)
        results = []
        for score, chunk_id in zip(scores[0], ids[0]):
            if chunk_id < 0:
                continue
            chunk = dict(self.chunks[chunk_id])
            chunk["score"] = float(score)
            results.append(chunk)
        return results
