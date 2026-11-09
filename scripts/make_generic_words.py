import json
from pathlib import Path

from wordfreq import zipf_frequency

from build_knowledge_base import RAW, collect, strip_possessive
from manual_terms import FORCE

THRESHOLD = 3.5
OUTPUT = Path(__file__).resolve().parent / "generic_words.json"


def main():
    texts = {p: p.read_text(encoding="utf-8") for p in sorted(RAW.glob("*.txt"))}
    _, total, _ = collect(texts)
    generic = sorted(
        base
        for base in total
        if base not in FORCE and base.isalpha() and zipf_frequency(base.lower(), "en") >= THRESHOLD
    )
    OUTPUT.write_text(json.dumps(generic, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"generic words: {len(generic)}")


if __name__ == "__main__":
    main()
