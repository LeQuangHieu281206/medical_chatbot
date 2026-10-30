# tests/18_inspect_failures.py
import random

import chromadb
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "app/db/chroma_db"
COLLECTION = "medical_kb_vimedaqa"
EMBED_MODEL = "intfloat/multilingual-e5-small"
N_QUESTIONS = 500
TOP_K = 10
SEED = 42  # cùng seed với bước 17 nên cùng tập câu hỏi


def norm(s):
    return " ".join((s or "").split())


def is_match(doc, gold):
    d, g = norm(doc), norm(gold)
    return bool(d and g) and (g in d or d in g)


def head(text, n=90):
    return norm(text)[:n]


def main():
    col = chromadb.PersistentClient(path=CHROMA_PATH).get_collection(COLLECTION)
    ds = load_dataset("tmnam20/ViMedAQA", "all", split="test")
    rows = [r for r in ds if norm(r["question"]) and norm(r["context"])]
    random.Random(SEED).shuffle(rows)
    rows = rows[:N_QUESTIONS]

    model = SentenceTransformer(EMBED_MODEL)
    embs = model.encode(
        [r["question"] for r in rows], batch_size=32, normalize_embeddings=True
    )

    misses, wrong_top1, ranks = [], [], []
    for i in range(0, len(rows), 50):
        res = col.query(
            query_embeddings=embs[i : i + 50].tolist(),
            n_results=TOP_K,
            include=["documents", "distances"],
        )
        for j, (docs, dists) in enumerate(zip(res["documents"], res["distances"])):
            row = rows[i + j]
            rank = next(
                (r + 1 for r, d in enumerate(docs) if is_match(d, row["context"])),
                None,
            )
            ranks.append(rank)
            item = (row, rank, docs, dists)
            if rank is None:
                misses.append(item)
            elif rank > 1:
                wrong_top1.append(item)

    n = len(ranks)
    print(f"R@1={sum(1 for r in ranks if r == 1)/n:.3f}  "
          f"R@2={sum(1 for r in ranks if r and r <= 2)/n:.3f}  "
          f"R@3={sum(1 for r in ranks if r and r <= 3)/n:.3f}\n")

    def show(title, items, limit):
        print("=" * 100)
        print(f"{title} ({len(items)} câu, hiển thị {min(limit, len(items))})")
        for row, rank, docs, dists in items[:limit]:
            print("-" * 100)
            print(f"Hỏi   : {row['question']}")
            print(f"Đúng  : [{row.get('topic')}] {head(row['context'])}")
            print(f"Hạng  : {rank}")
            for k in range(3):
                print(f"Top{k+1}  : d={dists[k]:.3f} {head(docs[k])}")

    show("KHÔNG TÌM THẤY TRONG TOP 10", misses, 16)
    random.Random(1).shuffle(wrong_top1)
    show("TÌM THẤY NHƯNG KHÔNG PHẢI HẠNG 1", wrong_top1, 8)


if __name__ == "__main__":
    main()