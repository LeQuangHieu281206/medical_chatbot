# tests/17_eval_retrieval.py
import random
import time

import chromadb
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "app/db/chroma_db"
COLLECTION = "medical_kb_vimedaqa"
EMBED_MODEL = "intfloat/multilingual-e5-small"
N_QUESTIONS = 500
TOP_K = 10
SEED = 42


def norm(s: str) -> str:
    return " ".join((s or "").split())


def is_match(doc: str, gold: str) -> bool:
    d, g = norm(doc), norm(gold)
    if not d or not g:
        return False
    return g in d or d in g


def evaluate(model, col, questions, golds, prefix):
    texts = [prefix + q for q in questions]
    t0 = time.time()
    embs = model.encode(
        texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False
    )
    t_embed = time.time() - t0

    ranks = []
    t0 = time.time()
    for i in range(0, len(texts), 50):
        res = col.query(
            query_embeddings=embs[i : i + 50].tolist(),
            n_results=TOP_K,
            include=["documents"],
        )
        for docs, gold in zip(res["documents"], golds[i : i + 50]):
            rank = next(
                (r + 1 for r, d in enumerate(docs) if is_match(d, gold)), None
            )
            ranks.append(rank)
    t_query = time.time() - t0

    n = len(ranks)
    out = {f"R@{k}": sum(1 for r in ranks if r and r <= k) / n for k in (1, 3, 5, 10)}
    out["MRR@10"] = sum(1 / r for r in ranks if r) / n
    out["embed_s"] = t_embed
    out["query_s"] = t_query
    return out, ranks


def main():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection(COLLECTION)
    print(f"Collection {COLLECTION}: {col.count()} document")

    sample = col.get(limit=1, include=["documents", "metadatas"])
    print("Metadata mẫu:", sample["metadatas"][0])
    print("Document mẫu:", sample["documents"][0][:150].replace("\n", " "), "...\n")

    ds = load_dataset("tmnam20/ViMedAQA", "all", split="test")
    rows = [r for r in ds if norm(r["question"]) and norm(r["context"])]
    random.Random(SEED).shuffle(rows)
    rows = rows[:N_QUESTIONS]
    questions = [r["question"] for r in rows]
    golds = [r["context"] for r in rows]
    print(f"Đánh giá {len(rows)} câu hỏi test\n")

    model = SentenceTransformer(EMBED_MODEL)

    for name, prefix in [("không tiền tố", ""), ("query: ", "query: ")]:
        res, ranks = evaluate(model, col, questions, golds, prefix)
        print(f"[{name}]")
        print(
            "  "
            + "  ".join(f"{k}={res[k]:.3f}" for k in ("R@1", "R@3", "R@5", "R@10", "MRR@10"))
        )
        print(f"  embed {res['embed_s']:.1f}s, truy vấn {res['query_s']:.1f}s")
        print(f"  không tìm thấy trong top {TOP_K}: {sum(1 for r in ranks if r is None)}\n")


if __name__ == "__main__":
    main()