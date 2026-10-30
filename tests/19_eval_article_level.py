# tests/19_eval_article_level.py
import random

import chromadb
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "app/db/chroma_db"
COLLECTION = "medical_kb_vimedaqa"
EMBED_MODEL = "intfloat/multilingual-e5-small"
N_QUESTIONS = 500
TOP_K = 10
SEED = 42  # cùng tập câu hỏi với bước 17 và 18


def norm(s):
    return " ".join((s or "").split())


def norm_url(u):
    return (u or "").strip().rstrip("/").lower()


def is_match(doc, gold):
    d, g = norm(doc), norm(gold)
    return bool(d and g) and (g in d or d in g)


def rate(ranks, k):
    return sum(1 for r in ranks if r and r <= k) / len(ranks)


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

    passage_ranks, article_ranks = [], []
    no_url = 0
    for i in range(0, len(rows), 50):
        res = col.query(
            query_embeddings=embs[i : i + 50].tolist(),
            n_results=TOP_K,
            include=["documents", "metadatas"],
        )
        for j, (docs, metas) in enumerate(zip(res["documents"], res["metadatas"])):
            row = rows[i + j]
            gold_url = norm_url(row.get("article_url"))
            if not gold_url:
                no_url += 1
            p_rank = next(
                (r + 1 for r, d in enumerate(docs) if is_match(d, row["context"])),
                None,
            )
            a_rank = next(
                (
                    r + 1
                    for r, m in enumerate(metas)
                    if gold_url and norm_url(m.get("link")) == gold_url
                ),
                None,
            )
            passage_ranks.append(p_rank)
            article_ranks.append(a_rank)

    n = len(rows)
    print(f"Số câu: {n}, thiếu article_url: {no_url}\n")
    for name, ranks in [("Mức đoạn", passage_ranks), ("Mức bài ", article_ranks)]:
        mrr = sum(1 / r for r in ranks if r) / n
        print(
            f"{name}: R@1={rate(ranks,1):.3f}  R@2={rate(ranks,2):.3f}  "
            f"R@3={rate(ranks,3):.3f}  R@10={rate(ranks,10):.3f}  MRR={mrr:.3f}"
        )

    not_first = [(p, a) for p, a in zip(passage_ranks, article_ranks) if p != 1]
    same_article_top1 = sum(1 for p, a in not_first if a == 1)
    print(
        f"\nTrong {len(not_first)} câu không đúng đoạn ở hạng 1: "
        f"{same_article_top1} câu có top 1 đúng bài "
        f"({same_article_top1 / max(1, len(not_first)):.1%})"
    )
    miss_article = sum(1 for a in article_ranks if a is None)
    print(f"Không thấy đúng bài trong top {TOP_K}: {miss_article} câu")


if __name__ == "__main__":
    main()