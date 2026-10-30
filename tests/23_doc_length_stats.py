# tests/23_doc_length_stats.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb

from app.services.topic_filter import COLLECTION, DB_PATH


def lengths(col):
    out = []
    for off in range(0, col.count(), 2000):
        res = col.get(limit=2000, offset=off, include=["documents"])
        out += [len(d) for d in res["documents"]]
    return sorted(out)


def pct(xs, p):
    return xs[min(len(xs) - 1, int(len(xs) * p))]


def main():
    client = chromadb.PersistentClient(path=DB_PATH)
    for name in (f"{COLLECTION}_vimedaqa", COLLECTION):
        xs = lengths(client.get_collection(name))
        n = len(xs)
        print(f"{name}: {n} document")
        print("  p25/p50/p75/p90/p95:", [pct(xs, p) for p in (0.25, 0.5, 0.75, 0.9, 0.95)])
        for lim in (500, 800, 1000):
            print(f"  dài hơn {lim} ký tự: {sum(1 for x in xs if x > lim) / n:.1%}")
        print()


if __name__ == "__main__":
    main()