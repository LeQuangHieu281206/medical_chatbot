"""Đo xem BM25 + RRF có kéo được tài liệu đúng chủ đề lên đầu không.

Bối cảnh đo được bằng ``tests/56_doc_recall.py``:
    - 19/19 câu có tài liệu đúng chủ đề trong 50 tài liệu gần nhất (dense)
    - nhưng 7 câu tài liệu đúng nằm ở hạng 4-27 nên không vào ngữ cảnh

Ý tưởng: giữ nguyên bể ứng viên dense (không cần index toàn kho), chấm thêm
điểm BM25 (khớp từ khoá) rồi gộp thứ hạng bằng RRF:

    RRF(d) = 1/(60 + hạng_dense) + 1/(60 + hạng_bm25)

RRF dùng THỨ HẠNG nên không phải so sánh hai loại điểm vốn không cùng đơn vị.

Cách chạy::

    .venv/bin/python tests/57_hybrid_recall.py
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _recall_patterns import PATTERNS  # noqa: E402

SRC = ROOT / "data" / "sources"
EVAL = SRC / "eval_answers_50.jsonl"
POOL = 20
RRF_K = 60

WORD = re.compile(r"[0-9a-zA-ZÀ-ỹ]+")


def tokenize(text: str) -> list[str]:
    return WORD.findall((text or "").lower())


def bm25_scores(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """BM25 đơn giản, tính tại chỗ trên bể ứng viên (không cần index)."""
    qtok = tokenize(query)
    toks = [tokenize(d) for d in docs]
    n = len(toks)
    avgdl = sum(len(t) for t in toks) / max(n, 1)
    df: dict[str, int] = {}
    for t in toks:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    scores = []
    for t in toks:
        tf: dict[str, int] = {}
        for w in t:
            tf[w] = tf.get(w, 0) + 1
        dl = len(t) or 1
        s = 0.0
        for w in qtok:
            if w not in tf:
                continue
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            f = tf[w]
            s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    return scores


def ranks_desc(scores: list[float], eps: float = 1e-9) -> list[int]:
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    out = [0] * len(scores)
    for pos, idx in enumerate(order, 1):
        out[idx] = pos
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=str(EVAL))
    args = ap.parse_args()

    from app.services.pipeline import MedicalChatbot

    ev = {json.loads(l)["id"]: json.loads(l)
          for l in open(args.eval, encoding="utf-8") if l.strip()}
    bot = MedicalChatbot()

    better = same = worse = 0
    rows = []
    for qid, pat in PATTERNS.items():
        if qid not in ev:
            continue
        q = ev[qid]["question"]
        emb = bot.embedder.encode([f"query: {q}"], normalize_embeddings=True).tolist()
        found_dense = found_hybrid = 0
        for col in (bot.encyc, bot.collection):
            if col is None:
                continue
            r = col.query(query_embeddings=emb, n_results=POOL,
                          include=["documents", "metadatas", "distances"])
            docs = r["documents"][0]
            dist = r["distances"][0]
            if not docs:
                continue
            idx_hit = [i for i, d in enumerate(docs) if d and re.search(pat, d, re.I)]
            if not idx_hit:
                continue
            dense_rank = sorted(range(len(docs)), key=lambda i: dist[i])
            dr = min(dense_rank.index(i) + 1 for i in idx_hit)

            bm = bm25_scores(q, docs)
            bm_rank = ranks_desc(bm)
            rrf = [1 / (RRF_K + (sorted(range(len(docs)), key=lambda i: dist[i]).index(i) + 1))
                   + 1 / (RRF_K + bm_rank[i]) for i in range(len(docs))]
            fused = ranks_desc(rrf)
            hr = min(fused[i] for i in idx_hit)

            if not found_dense or dr < found_dense:
                found_dense = dr
            if not found_hybrid or hr < found_hybrid:
                found_hybrid = hr
        if not found_dense:
            continue
        rows.append((qid, found_dense, found_hybrid))
        if found_hybrid < found_dense:
            better += 1
        elif found_hybrid > found_dense:
            worse += 1
        else:
            same += 1

    print(f"{'id':<6}{'hạng dense':>12}{'hạng RRF':>10}   vào top-2?")
    print("-" * 58)
    d2 = h2 = 0
    for qid, dr, hr in rows:
        d2 += dr <= 2
        h2 += hr <= 2
        print(f"{qid:<6}{dr:>12}{hr:>10}   dense {'Y' if dr <= 2 else 'N'} / rrf {'Y' if hr <= 2 else 'N'}")
    print("-" * 58)
    print(f"RRF tốt hơn: {better} | bằng: {same} | tệ hơn: {worse}")
    print(f"tài liệu đúng vào top-2: dense {d2}/{len(rows)} -> RRF {h2}/{len(rows)}")
    print("\nTiêu chí dùng: chỉ đưa BM25+RRF vào production nếu h2 - d2 >= 3 câu.")


if __name__ == "__main__":
    main()
