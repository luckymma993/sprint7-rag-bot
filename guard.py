import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bignore\b[^.\n]{0,40}\binstructions?\b",
        r"\bdisregard\b[^.\n]{0,40}\b(?:instructions?|rules?|above)\b",
        r"\bforget\b[^.\n]{0,40}\b(?:instructions?|rules?)\b",
        r"\byou\s+are\s+now\b",
        r"\b(?:system|developer)\s+(?:prompt|message)\b",
        r"\bnew\s+instructions?\b",
        r"\boutput\s*:",
        r"игнорир\w*[^.\n]{0,40}(?:инструкци|указани|правил)",
        r"забуд\w*[^.\n]{0,40}(?:инструкци|правил)",
    ]
]
SECRET_DISCLOSURE = re.compile(
    r"(?:парол|passw|credential|секрет|secret|api[\s_-]?key|токен|token)\w*"
    r"[^\n]{0,60}?[:=]\s*[\"«']?[\w.@/+-]{4,}",
    re.IGNORECASE,
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass(frozen=True)
class Guard:
    name: str
    preprompt: bool
    drop_chunks: bool
    strip_constructs: bool
    output_check: bool


GUARD_MODES = {
    "off": Guard("off", False, False, False, False),
    "preprompt": Guard("preprompt", True, False, False, False),
    "strip": Guard("strip", False, False, True, False),
    "drop": Guard("drop", False, True, False, False),
    "output": Guard("output", False, False, False, True),
    "all": Guard("all", True, True, True, True),
}


def is_suspicious(text):
    return any(pattern.search(text) for pattern in INJECTION_PATTERNS)


def leaks_secret(text):
    return bool(SECRET_DISCLOSURE.search(text))


def strip_constructs(text):
    parts = SENTENCE_SPLIT.split(text)
    kept = [part for part in parts if part and not is_suspicious(part)]
    return " ".join(kept)


def apply_to_chunks(chunks, guard):
    kept, dropped, stripped = [], [], []
    for chunk in chunks:
        text = chunk["text"]
        if guard.drop_chunks and is_suspicious(text):
            dropped.append(chunk["source"])
            continue
        if guard.strip_constructs and is_suspicious(text):
            cleaned = strip_constructs(text)
            stripped.append(chunk["source"])
            if not cleaned.strip():
                dropped.append(chunk["source"])
                continue
            chunk = {**chunk, "text": cleaned}
        kept.append(chunk)
    return kept, dropped, stripped
