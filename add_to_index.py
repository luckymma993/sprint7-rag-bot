import argparse
import json
from pathlib import Path

import faiss
import numpy as np

import build_index as builder
import index_common as common


def main():
    parser = argparse.ArgumentParser(description="Copy the index and add documents from a folder")
    parser.add_argument("source_dir")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)
    chunks = common.load_chunks_from(common.CHUNKS_FILE)
    index = faiss.read_index(str(common.INDEX_FILE))
    splitter = builder.make_splitter()

    added = []
    for path in sorted(Path(args.source_dir).glob("*.md")):
        added.extend(builder.split_document(path, splitter))
    for offset, chunk in enumerate(added):
        chunk["id"] = len(chunks) + offset

    model = common.load_model()
    vectors = model.encode(
        [builder.embedding_text(chunk) for chunk in added],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)
    index.add(vectors)
    chunks.extend(added)

    faiss.write_index(index, str(out_dir / "faiss.index"))
    with (out_dir / "chunks.jsonl").open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"added {len(added)} chunks from {args.source_dir}, total {len(chunks)} in {out_dir}")
    for chunk in added:
        print(chunk["id"], chunk["source"], chunk["words"], "words")


if __name__ == "__main__":
    main()
