"""Chẩn đoán mảng dữ liệu yếu: recall@k tách theo topic và theo dạng câu hỏi.

Dùng ViMedAQA test (có metadata topic: body-part / disease / drug / medicine) để biết
mảng nào cần bổ sung dữ liệu trước khi nạp thêm corpus.
"""
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

DB_PATH = "app/db/chroma_db"
COLLECTION = "medical_kb_vimedaqa"
EMBED_MODEL = "intfloat/multilingual-e5-small"
N_QUESTIONS = 600
TOP_K = 10
SEED = 42

WH = [
    ("what", re.compile(r"\b(là gì|gì|bao gồm|khái niệm)\b", re.I)),
    ("why", re.compile(r"\b(tại sao|vì sao|nguyên nhân|do đâu)\b", re.I)),
    ("how", re.compile(r"\b(như thế nào|thế nào|cách|bao lâu|làm sao)\b", re.I)),
    ("which_drug", re.compile(r"\b(thuốc gì|dùng thuốc|điều trị|chữa)\b", re.I)),
    ("when", re.compile(r"\b(khi nào|bao giờ|lúc nào)\b", re.I)),
]


def norm(s):
    return " ".join((s or "").split())


def is_match(doc, gold):
    d, g = norm(doc), norm(gold)
    return bool(d and g and (g in d or d in g))


def bucket(q):
    for name, rx in WH:
        if rx.search(q):
            return name
    return "other"


def report(name, ranks):
    n = len(ranks)
    if not n:
        return
    r1 = sum(1 for r in ranks if r and r <= 1) / n
    r3 = sum(1 for r in ranks if r and r <= 3) / n
    r10 = sum(1 for r in ranks if r and r <= TOP_K) / n
    mrr = sum(1 / r for r in ranks if r) / n
    miss = sum(1 for r in ranks if r is None)
    print(f"{name:<14}{n:>5}{r1:>8.3f}{r3:>8.3f}{r10:>8.3f}{mrr:>9.3f}{miss:>7}")


def main():
    col = chromadb.PersistentClient(path=DB_PATH).get_collection(COLLECTION)
    print(f"{COLLECTION}: {col.count()} đoạn")
    ds = load_dataset("tmnam20/ViMedAQA", "all", split="test")
    rows = [r for r in ds if norm(r["question"]) and norm(r["context"])]
    random.Random(SEED).shuffle(rows)
    rows = rows[:N_QUESTIONS]

    model = SentenceTransformer(EMBED_MODEL)
    embs = model.encode([f"query: {r['question']}" for r in rows],
                        batch_size=32, normalize_embeddings=True,
                        show_progress_bar=False).tolist()

    by_topic, by_wh = defaultdict(list), defaultdict(list)
    for r, emb in zip(rows, embs):
        res = col.query(query_embeddings=[emb], n_results=TOP_K, include=["documents"])
        docs = res["documents"][0]
        rank = next((i + 1 for i, d in enumerate(docs) if is_match(d, r["context"])), None)
        topic = str(r.get("topic"))
        by_topic[topic].append(rank)
        by_wh[bucket(r["question"])].append(rank)

    TOPIC = {"0": "body-part", "1": "disease", "2": "drug", "3": "medicine"}
    print(f"\n{'mảng':<14}{'n':>5}{'R@1':>8}{'R@3':>8}{'R@10':>8}{'MRR@10':>9}{'miss':>7}")
    report("TẤT CẢ", [r for v in by_topic.values() for r in v])
    for t, ranks in sorted(by_topic.items()):
        report(TOPIC.get(t, t), ranks)
    print()
    for k, ranks in sorted(by_wh.items()):
        report(k, ranks)


if __name__ == "__main__":
    main()
