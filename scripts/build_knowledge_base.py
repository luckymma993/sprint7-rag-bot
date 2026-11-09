import collections
import json
import random
import re
import sys
from pathlib import Path

from manual_terms import DEMONYMS, FORCE, KEEP, PHRASES, SW_VOCAB, WORDS

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "knowledge_base"
MAP_FILE = ROOT / "terms_map.json"
GENERIC_FILE = Path(__file__).resolve().parent / "generic_words.json"
SEED = 20241107

UP = "A-Z0-9À-ÖØ-Þ"
TOKEN = re.compile(rf"(?<!\w)[{UP}][\w'’]*(?:-[{UP}][\w'’]*)*")
LOWER_WORD = re.compile(r"(?<!\w)[a-z][a-z'’\-]*")
POSSESSIVE = re.compile(r"(['’]s|['’])$")

ONSETS = [
    "Xa", "Ve", "Kor", "Tha", "Zel", "Mar", "Dra", "Ka", "Lor", "Syl", "Bre", "Ur",
    "Ol", "Ny", "Fen", "Gar", "Hal", "Ir", "Jax", "Quin", "Rho", "Sal", "Tev", "Vor",
    "Wen", "Yar", "Zun", "Cae", "Dov", "Eld", "Fy", "Gis", "Hy", "Ith", "Jor", "Kes",
    "Lun", "Mor", "Nev", "Oph", "Pyr", "Qua", "Rin", "Sov", "Tor", "Ulv", "Vash",
    "Wyn", "Xel", "Yth", "Zar", "Bael", "Cyr", "Dael", "Esk", "Fael", "Grim", "Havr",
]
CODAS = [
    "rn", "lgor", "ven", "dun", "krix", "thas", "mir", "lan", "goth", "ria", "phen",
    "dak", "sul", "nor", "zek", "vash", "rel", "tos", "ul", "ix", "on", "ar", "eth",
    "yn", "mara", "tia", "dris", "vok", "lume", "rax", "wyn", "sera", "thil", "gan",
    "zor", "phos", "kai", "lis", "mund", "bryn", "dren", "vael", "thos", "kern",
]


def strip_possessive(token):
    return POSSESSIVE.sub("", token)


def is_code(token):
    if re.fullmatch(r"\d+(?:st|nd|rd|th|m|km|cm|mm|kg|s)", token):
        return False
    has_digit = any(ch.isdigit() for ch in token)
    has_alpha = any(ch.isalpha() for ch in token)
    if has_digit and has_alpha and len(token) >= 2:
        return True
    return bool(re.fullmatch(r"[A-Z]{2,}-[A-Z]{2,}", token))


def make_code(token, rng, used):
    for _ in range(200):
        mapping = {}
        out = []
        for ch in token:
            if ch.isdigit():
                mapping.setdefault(ch, str(rng.randint(1, 9)))
            elif ch.isalpha():
                mapping.setdefault(ch, rng.choice("BCDFGHJKLMNPQRSTVWXZ"))
            else:
                mapping.setdefault(ch, ch)
            out.append(mapping[ch])
        value = "".join(out)
        if value != token and value not in used:
            return value
    raise RuntimeError(f"no code for {token}")


def make_name(rng, used, lowercase_vocab):
    for _ in range(500):
        value = rng.choice(ONSETS) + rng.choice(CODAS)
        if rng.random() < 0.15:
            value += rng.choice(CODAS)
        if len(value) < 5 or value in used or value.lower() in lowercase_vocab:
            continue
        return value
    raise RuntimeError("no name")


def collect(texts):
    lowercase_vocab = set()
    total = collections.Counter()
    mid = collections.Counter()
    for text in texts.values():
        lowercase_vocab.update(w.lower() for w in LOWER_WORD.findall(text))
        for line in text.splitlines():
            for sentence in re.split(r"(?<=[.!?])\s+", line):
                for match in TOKEN.finditer(sentence):
                    base = strip_possessive(match.group(0))
                    total[base] += 1
                    if match.start() > 0 and not sentence.startswith("#"):
                        mid[base] += 1
    return lowercase_vocab, total, mid


def pick_candidates(total, mid, lowercase_vocab, phrase_keys):
    generic = set(json.loads(GENERIC_FILE.read_text(encoding="utf-8")))
    candidates = set()
    start_only = []
    for base, count in total.items():
        if len(base) < 2 or base in KEEP or base in phrase_keys or (base in generic and base not in FORCE):
            continue
        if re.fullmatch(r"[\d,.]+", base) or not any(ch.isalpha() for ch in base):
            continue
        if re.fullmatch(r"\d+(?:st|nd|rd|th|m|km|cm|mm|kg|s)", base):
            continue
        if base in FORCE or is_code(base):
            candidates.add(base)
            continue
        if mid[base] == 0:
            start_only.append((base, count))
            continue
        candidates.add(base)
    return candidates, start_only


def assign_values(candidates, lowercase_vocab):
    rng = random.Random(SEED)
    used = set(candidates)
    values = {}
    for base in sorted(candidates):
        if base in DEMONYMS or (base.endswith("s") and base[:-1] in DEMONYMS):
            continue
        if base.endswith("s") and base[:-1] in candidates and not is_code(base):
            continue
        value = make_code(base, rng, used) if is_code(base) else make_name(rng, used, lowercase_vocab)
        used.add(value)
        values[base] = value
    for demonym, place in DEMONYMS.items():
        if place not in values:
            values[place] = make_name(rng, used, lowercase_vocab)
            used.add(values[place])
        stem = values[place]
        suffix = "n" if stem[-1] in "aeiouy" else "ian"
        values[demonym] = stem + suffix
        values[demonym + "s"] = stem + suffix + "s"
    for base in sorted(candidates):
        if base not in values and base.endswith("s") and base[:-1] in values:
            values[base] = values[base[:-1]] + "s"
    return values


def word_entries():
    entries = {}
    for word, value in WORDS.items():
        entries[word] = value
        entries[word + "s"] = value + "s"
        entries[word.capitalize()] = value.capitalize()
        entries[word.capitalize() + "s"] = value.capitalize() + "s"
    return entries


def lowercase_entries(token_values, lowercase_vocab):
    lower_map = {
        base.lower(): value.lower()
        for base, value in token_values.items()
        if base.lower() in lowercase_vocab and len(base) >= 5 and base not in FORCE
        and base.isalpha()
    }
    entries = dict(lower_map)
    for word in lowercase_vocab:
        if word.endswith("s") and word[:-1] in lower_map:
            entries[word] = lower_map[word[:-1]] + "s"
    return entries


def build_entries(token_values, lowercase_vocab):
    entries = {}
    entries.update(lowercase_entries(token_values, lowercase_vocab))
    entries.update(token_values)
    entries.update(word_entries())
    entries.update(PHRASES)
    return entries


def compile_pattern(entries):
    keys = sorted(entries, key=lambda k: (-len(k), k))
    body = "|".join(re.escape(k) for k in keys)
    return re.compile(rf"(?<!\w)(?:{body})(?!\w)")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def leak_report(outputs, entries, lowercase_vocab):
    generated = {w.lower() for v in entries.values() for w in re.findall(r"[\w'’-]+", v)}
    print("\n== franchise words still present ==")
    corpus = "\n".join(outputs.values())
    for term in SW_VOCAB:
        pattern = re.compile(rf"(?<!\w){re.escape(term.strip())}(?!\w)", re.IGNORECASE)
        found = list(pattern.finditer(corpus))
        if found:
            first = found[0]
            context = corpus[max(0, first.start() - 35): first.end() + 25].replace("\n", " ")
            print(f"{term.strip()!r}: {len(found)}  ...{context}...")
    print("\n== capitalized words left untouched (count) ==")
    left = collections.Counter()
    for text in outputs.values():
        for line in text.splitlines():
            for sentence in re.split(r"(?<=[.!?])\s+", line):
                for match in TOKEN.finditer(sentence):
                    base = strip_possessive(match.group(0))
                    if match.start() == 0 or base in KEEP or base.lower() in generated:
                        continue
                    if re.fullmatch(r"[\d,.]+", base):
                        continue
                    left[base] += 1
    print(" | ".join(f"{w}:{c}" for w, c in left.most_common(120)))


def main():
    report = "--report" in sys.argv
    texts = {p: p.read_text(encoding="utf-8") for p in sorted(RAW.glob("*.txt"))}
    lowercase_vocab, total, mid = collect(texts)
    candidates, start_only = pick_candidates(total, mid, lowercase_vocab, set(PHRASES))
    token_values = assign_values(candidates, lowercase_vocab)
    entries = build_entries(token_values, lowercase_vocab)
    pattern = compile_pattern(entries)

    outputs = {}
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.md"):
        old.unlink()
    for path, text in texts.items():
        replaced = pattern.sub(lambda m: entries[m.group(0)], text)
        title = replaced.splitlines()[0].lstrip("# ").strip()
        name = slugify(title) + ".md"
        (OUT / name).write_text(replaced, encoding="utf-8")
        outputs[name] = replaced

    MAP_FILE.write_text(
        json.dumps(dict(sorted(entries.items())), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"documents: {len(outputs)}, entries in map: {len(entries)}")
    if report:
        print("\n== start-only capitalized words (not replaced) ==")
        print(" | ".join(f"{w}:{c}" for w, c in sorted(start_only, key=lambda x: -x[1])[:80]))
        print("\n== names generated automatically ==")
        print(" | ".join(sorted(token_values)))
        leak_report(outputs, entries, lowercase_vocab)


if __name__ == "__main__":
    main()
