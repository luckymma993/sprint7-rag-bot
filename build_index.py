import json
import re
import time
from datetime import date

import faiss
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

import index_common as common

CHUNK_WORDS = 240
OVERLAP_WORDS = 40
MIN_WORDS = 60
MAX_MERGED_WORDS = 300
BATCH_SIZE = 16
HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def word_count(text):
    return len(text.split())


def make_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_WORDS,
        chunk_overlap=OVERLAP_WORDS,
        length_function=word_count,
        separators=["\n\n", "\n", r"(?<=[.!?])\s+", r"\s+", ""],
        is_separator_regex=True,
        keep_separator="end",
    )


def section_path(headings, position):
    stack = []
    for start, level, title in headings:
        if start > position:
            break
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
    return " > ".join(title for level, title in stack if level >= 2)


def locate(text, pieces):
    spans = []
    cursor = 0
    for piece in pieces:
        start = text.find(piece, cursor)
        if start < 0:
            start = text.find(piece[:80], cursor)
        if start < 0:
            start = cursor
        spans.append([start, start + len(piece)])
        cursor = start + 1
    return spans


def merge_small(text, spans):
    merged = []
    for start, end in spans:
        if merged and word_count(text[start:end]) < MIN_WORDS:
            previous_start, previous_end = merged[-1]
            if word_count(text[previous_start:end]) <= MAX_MERGED_WORDS:
                merged[-1] = [previous_start, max(previous_end, end)]
                continue
        merged.append([start, end])
    if len(merged) > 1 and word_count(text[merged[0][0]:merged[0][1]]) < MIN_WORDS:
        merged[0:2] = [[merged[0][0], merged[1][1]]]
    return merged


def split_document(path, splitter):
    text = path.read_text(encoding="utf-8")
    headings = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in HEADING.finditer(text)]
    title = headings[0][2] if headings else path.stem
    spans = merge_small(text, locate(text, splitter.split_text(text)))
    chunks = []
    for index, (start, end) in enumerate(spans):
        chunk_text = text[start:end].strip()
        chunks.append({
            "source": f"{path.parent.name}/{path.name}",
            "title": title,
            "section": section_path(headings, start),
            "chunk_index": index,
            "chunks_in_doc": len(spans),
            "start": start,
            "words": word_count(chunk_text),
            "text": chunk_text,
        })
    return chunks


def embedding_text(chunk):
    header = chunk["title"] + (f" — {chunk['section']}" if chunk["section"] else "")
    return f"{common.PASSAGE_PREFIX}{header}\n{chunk['text']}"


def main():
    started = time.perf_counter()
    splitter = make_splitter()
    files = sorted(common.KB_DIR.glob("*.md"))
    chunks = []
    for path in files:
        chunks.extend(split_document(path, splitter))
    for chunk_id, chunk in enumerate(chunks):
        chunk["id"] = chunk_id
    print(f"documents: {len(files)}, chunks: {len(chunks)}")

    model = common.load_model()
    texts = [embedding_text(chunk) for chunk in chunks]
    token_counts = [len(model.tokenizer(text)["input_ids"]) for text in texts]
    over_limit = sum(count > model.max_seq_length for count in token_counts)

    embed_started = time.perf_counter()
    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    ).astype(np.float32)
    embed_seconds = time.perf_counter() - embed_started

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    common.INDEX_DIR.mkdir(exist_ok=True)
    faiss.write_index(index, str(common.INDEX_FILE))
    with common.CHUNKS_FILE.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    words = [chunk["words"] for chunk in chunks]
    total_seconds = time.perf_counter() - started
    info = {
        "built": date.today().isoformat(),
        "model": common.MODEL_NAME,
        "embedding_dimensions": int(vectors.shape[1]),
        "index_type": "faiss.IndexFlatIP (cosine similarity on normalized vectors)",
        "documents": len(files),
        "chunks": len(chunks),
        "chunk_words_target": CHUNK_WORDS,
        "chunk_overlap_words": OVERLAP_WORDS,
        "chunk_words_min": min(words),
        "chunk_words_median": int(np.median(words)),
        "chunk_words_max": max(words),
        "chunks_over_token_limit": int(over_limit),
        "max_tokens_per_chunk": int(max(token_counts)),
        "embedding_seconds": round(embed_seconds, 1),
        "total_seconds": round(total_seconds, 1),
        "index_file_kb": round(common.INDEX_FILE.stat().st_size / 1024, 1),
        "chunks_file_kb": round(common.CHUNKS_FILE.stat().st_size / 1024, 1),
    }
    common.INFO_FILE.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
