"""So sánh truy xuất giữa medical_kb (mỗi dòng = 1 cặp Q&A) và medical_kb_v2 (đã tách chunk).

Câu hỏi lấy từ data/processed/eval.jsonl — bộ này đã bị loại khỏi KB khi prepare_data,
nên không có chuyện khớp đáp án sẵn trong DB.

Không đo được "đúng đáp án" tuyệt đối, nên đo 3 tín hiệu so sánh được:
  - khoảng cách cosine top-1 (nhỏ hơn = tự tin hơn)
  - độ phủ từ của đáp án vàng trong đoạn lấy về (coverage, lớn hơn = lấy đúng nội dung)
  - tỉ lệ câu có top-1 phủ >= 0.20

Chạy: .venv/bin/python tests/41_eval_qa_retrieval.py [--n 500]
"""
import argparse
import json
import random
import re
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from sentence_transformers import SentenceTransformer

from app.services.topic_filter import DB_PATH, EMBED_MODEL

EVAL = Path("data/processed/eval.jsonl")
COLLECTIONS = ["medical_kb", "medical_kb_v2"]
SEED = 42
WORD_RE = re.compile(r"\w+", re.UNICODE)


def toks(text):
    return set(WORD_RE.findall(unicodedata.normalize("NFC", text or "").lower()))


def pct(vals, q):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(q * len(vals)))]


def evaluate(model, col, rows, k=3):
    embs = model.encode([f"query: {r['question']}" for r in rows], batch_size=32,
                        normalize_embeddings=True, show_progress_bar=False).tolist()
    dists, cov1, cov3, covu, lat = [], [], [], [], []
    for emb, r in zip(embs, rows):
        t0 = time.perf_counter()
        res = col.query(query_embeddings=[emb], n_results=k, include=["documents", "distances"])
        lat.append(time.perf_counter() - t0)
        docs = res["documents"][0]
        dists.append(res["distances"][0][0])
        gold = toks(r["answer"])
        if not gold:
            continue
        union = set()
        for d in docs:
            union |= toks(d)
        cov1.append(len(gold & toks(docs[0])) / len(gold))
        cov3.append(max(len(gold & toks(d)) for d in docs) / len(gold))
        covu.append(len(gold & union) / len(gold))
    return {
        "n": len(dists),
        "d_top1": sum(dists) / len(dists),
        "cov1": sum(cov1) / len(cov1),
        "cov3": sum(cov3) / len(cov3),
        "cov_union3": sum(covu) / len(covu),
        "hit20": sum(1 for c in cov1 if c >= 0.20) / len(cov1),
        "p95_ms": 1000 * pct(lat, 0.95),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    args = ap.parse_args()

    rows = [json.loads(l) for l in EVAL.open(encoding="utf-8") if l.strip()]
    random.Random(SEED).shuffle(rows)
    rows = rows[:args.n]
    print(f"Đánh giá trên {len(rows)} câu hỏi từ {EVAL}\n")

    model = SentenceTransformer(EMBED_MODEL)
    client = chromadb.PersistentClient(path=DB_PATH)

    print(f"{'collection':<18}{'n':>5}{'d_top1':>9}{'cov@1':>8}{'cov@3':>8}"
          f"{'covUni3':>9}{'hit20':>8}{'p95ms':>8}{'số doc':>9}")
    for name in COLLECTIONS:
        try:
            col = client.get_collection(name)
        except Exception:
            print(f"{name:<18} (chưa có collection)")
            continue
        m = evaluate(model, col, rows)
        print(f"{name:<18}{m['n']:>5}{m['d_top1']:>9.4f}{m['cov1']:>8.3f}"
              f"{m['cov3']:>8.3f}{m['cov_union3']:>9.3f}{m['hit20']:>8.3f}"
              f"{m['p95_ms']:>8.1f}{col.count():>9}")


if __name__ == "__main__":
    main()
