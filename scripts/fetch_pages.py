import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

import requests

API = "https://starwars.fandom.com/api.php"
HEADERS = {"User-Agent": "student-project-rag/1.0 (educational RAG project)"}
ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "raw_html"
TEXT_DIR = ROOT / "raw"
MAX_WORDS = 1500
MIN_WORDS = 350
PAUSE = 1.2

TITLES = [
    "Darth Vader", "Luke Skywalker", "Leia Organa", "Han Solo", "Obi-Wan Kenobi",
    "Yoda", "Sheev Palpatine", "Chewbacca", "Darth Maul", "Boba Fett",
    "Jabba Desilijic Tiure", "Lando Calrissian", "C-3PO", "R2-D2", "Padmé Amidala",
    "Qui-Gon Jinn", "Mace Windu", "Dooku", "Grievous", "Wilhuff Tarkin",
    "Ahsoka Tano", "Kylo Ren", "Rey", "Poe Dameron",
    "Tatooine", "Alderaan", "Hoth", "Endor", "Naboo", "Coruscant", "Kamino",
    "Dagobah", "Bespin", "Mustafar", "Geonosis", "Kashyyyk", "Yavin 4", "Jakku", "Scarif",
    "DS-1 Orbital Battle Station", "Millennium Falcon", "X-wing starfighter", "Lightsaber", "Hyperdrive",
    "Blaster", "All Terrain Armored Transport", "Imperial-class Star Destroyer",
    "Kyber crystal", "Droid",
    "Galactic Empire", "Alliance to Restore the Republic", "Jedi", "Sith",
    "Galactic Republic", "Clone Wars", "Battle of Yavin", "Battle of Hoth",
    "Order 66", "First Order", "Stormtrooper",
]

STOP_HEADINGS = {
    "behind the scenes", "appearances", "non-canon appearances", "sources",
    "non-canon sources", "notes and references", "external links", "see also",
    "gallery", "legends", "references", "notes", "in-universe locations",
}
SKIP_TAGS = {"table", "aside", "sup", "style", "script", "figure", "noscript", "nav"}
SKIP_CLASSES = {
    "dablink", "hatnote", "toc", "navbox", "reflist", "references", "thumb",
    "gallery", "mw-editsection", "noprint", "navigation", "cquote", "quote",
    "portable-infobox", "wds-collapsible", "mbox", "tmbox", "ambox", "tabber",
}
VOID_TAGS = {"br", "img", "hr", "meta", "link", "input", "wbr"}
BLOCK_TAGS = {"p", "h2", "h3", "h4", "li"}


class Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.blocks = []
        self.current = None
        self.stopped = False

    def skipping(self):
        return any(flag for _, flag in self.stack)

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            if tag == "br" and self.current is not None and not self.skipping():
                self.current["text"].append(" ")
            return
        classes = set((dict(attrs).get("class") or "").split())
        flag = tag in SKIP_TAGS or bool(classes & SKIP_CLASSES)
        self.stack.append((tag, flag))
        if flag or self.skipping() or self.stopped:
            return
        if tag in BLOCK_TAGS and self.current is None:
            self.current = {"tag": tag, "text": []}

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                popped = self.stack[i:]
                del self.stack[i:]
                break
        else:
            return
        if tag in BLOCK_TAGS and self.current is not None and self.current["tag"] == tag:
            if not any(flag for _, flag in popped):
                self.finish_block()
            self.current = None

    def handle_data(self, data):
        if self.current is not None and not self.skipping() and not self.stopped:
            self.current["text"].append(data)

    def finish_block(self):
        text = re.sub(r"\s+", " ", "".join(self.current["text"])).strip()
        tag = self.current["tag"]
        if not text:
            return
        if tag in {"h2", "h3", "h4"}:
            title = text.replace("[]", "").strip()
            if tag == "h2" and title.lower() in STOP_HEADINGS:
                self.stopped = True
                return
            level = {"h2": "##", "h3": "###", "h4": "####"}[tag]
            self.blocks.append(f"{level} {title}")
        elif tag == "li":
            if len(text) > 40:
                self.blocks.append(f"- {text}")
        else:
            if len(text) > 30:
                self.blocks.append(text)


def fetch_html(title):
    cache = HTML_DIR / (slug(title) + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    params = {
        "action": "parse", "page": title, "prop": "text", "format": "json",
        "redirects": 1, "disablelimitreport": 1, "disableeditsection": 1,
    }
    for attempt in range(3):
        try:
            response = requests.get(API, params=params, headers=HEADERS, timeout=60)
            response.raise_for_status()
            data = response.json()
            cache.write_text(json.dumps(data), encoding="utf-8")
            time.sleep(PAUSE)
            return data
        except Exception as error:
            print(f"retry {title}: {error}", file=sys.stderr)
            time.sleep(3)
    return None


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def cap_words(blocks):
    result, count = [], 0
    for block in blocks:
        words = len(block.split())
        if count + words > MAX_WORDS and count >= MIN_WORDS:
            break
        result.append(block)
        count += words
    while result and result[-1].startswith("#"):
        result.pop()
    return result, count


def main():
    HTML_DIR.mkdir(exist_ok=True)
    TEXT_DIR.mkdir(exist_ok=True)
    kept, skipped = [], []
    for title in TITLES:
        data = fetch_html(title)
        if not data or "parse" not in data:
            skipped.append((title, "no data"))
            continue
        parser = Cleaner()
        parser.feed(data["parse"]["text"]["*"])
        blocks, words = cap_words(parser.blocks)
        if words < MIN_WORDS:
            skipped.append((title, f"{words} words"))
            continue
        heading = data["parse"]["title"]
        text = f"# {heading}\n\n" + "\n\n".join(blocks) + "\n"
        (TEXT_DIR / (slug(title) + ".txt")).write_text(text, encoding="utf-8")
        kept.append((title, words))
        print(f"ok {title}: {words} words")
    print(f"\nkept {len(kept)}, skipped {len(skipped)}")
    for item in skipped:
        print("skipped", item)


if __name__ == "__main__":
    main()
