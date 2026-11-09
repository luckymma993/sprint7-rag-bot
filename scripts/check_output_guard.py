import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from guard import leaks_secret

total = 0
hits = []
for path in sorted(glob.glob("logs/*.jsonl")):
    with open(path, encoding="utf-8") as file:
        for line in file:
            row = json.loads(line)
            if "text" not in row:
                continue
            total += 1
            if leaks_secret(row["text"]):
                hits.append((os.path.basename(path), row["question"][:50], row.get("guard")))
print("answers checked:", total)
for hit in hits:
    print("match:", hit)

with open("index/chunks.jsonl", encoding="utf-8") as file:
    chunks = [json.loads(line) for line in file]
print("clean chunks matching the pattern:", sum(leaks_secret(chunk["text"]) for chunk in chunks), "of", len(chunks))
