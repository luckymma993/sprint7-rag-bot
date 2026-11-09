import argparse

from index_common import Searcher


def show(results):
    for rank, chunk in enumerate(results, start=1):
        place = chunk["title"] + (f" > {chunk['section']}" if chunk["section"] else "")
        snippet = " ".join(chunk["text"].split())[:260]
        print(f"{rank}. score={chunk['score']:.3f}  {chunk['source']}  chunk {chunk['chunk_index'] + 1}/{chunk['chunks_in_doc']}")
        print(f"   {place}")
        print(f"   {snippet}...")


def main():
    parser = argparse.ArgumentParser(description="Search the FAISS index of the knowledge base")
    parser.add_argument("query")
    parser.add_argument("-k", type=int, default=3)
    args = parser.parse_args()
    show(Searcher().search(args.query, args.k))


if __name__ == "__main__":
    main()
