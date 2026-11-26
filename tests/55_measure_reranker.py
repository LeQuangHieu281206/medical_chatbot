"""Đo tác dụng của rerank cross-encoder so với chỉ dùng khoảng cách vector.

Cách đo (không cần LLM, không cần chấm điểm bằng tay):

1. Lấy 10 tài liệu gần nhất từ mỗi collection bằng dense search (như hiện tại).
2. Chấm lại từng cặp (câu hỏi, đoạn văn) bằng cross-encoder, sắp lại.
3. Tính *độ phủ từ khoá*: bao nhiêu phần trăm từ nội dung trong ``reference_facts``
   (đáp án chuẩn) xuất hiện trong tài liệu đứng đầu.
   - dense top-1 phủ thấp mà rerank top-1 phủ cao  -> rerank sửa được
   - cả hai đều thấp                                -> kho không có bài phù hợp
4. In phân bố điểm rerank để chọn ngưỡng "dùng tài liệu hay bỏ".

Cách chạy::

    .venv/bin/python tests/55_measure_reranker.py            # cả 50 câu
    .venv/bin/python tests/55_measure_reranker.py --limit 8  # chạy thử
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SRC = ROOT / "data" / "sources"
EVAL = SRC / "eval_answers_50.jsonl"
POOL_PER_COLLECTION = 10

STOP = set("""là của và có không các những được cho khi nếu thì này đó người bệnh
triệu chứng dấu hiệu thường thể có thể cần nên phải sẽ đã đang rất hơn như về
trong ngoài trên dưới một hai ba khi nào cách làm gì đây bị mắc gặp do vì nên
cũng nhưng mà ở tới từ với ra vào lên xuống rồi ạ nhé ạ.""".split())

WORD = re.compile(r"[0-9a-zA-ZÀ-ỹ]+")


def key_terms(facts: list[str]) -> set[str]:
    """Từ khoá nội dung của đáp án chuẩn (bỏ từ dừng, bỏ từ quá ngắn)."""
    terms = set()
    for fact in facts:
        for w in WORD.findall(fact.lower()):
            if len(w) >= 3 and w not in STOP:
                terms.add(w)
    return terms


def coverage(doc_text: str, terms: set[str]) -> float:
    if not terms:
        return 0.0
    text = doc_text.lower()
    hit = sum(1 for t in terms if t in text)
    return hit / len(terms)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=str(EVAL))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show", default="q02,q08,q11,q12,q04,q22,q37,q39",
                    help="id cần in chi tiết trước/sau khi rerank")
    args = ap.parse_args()

    from app.services import reranker
    from app.services.pipeline import MedicalChatbot

    if not reranker.available():
        print("Không nạp được reranker:", reranker.last_error())
        return
    print("Reranker:", reranker.MODEL_NAME)

    items = [json.loads(l) for l in open(args.eval, encoding="utf-8") if l.strip()]
    if args.limit:
        items = items[: args.limit]
    show = {x.strip() for x in args.show.split(",") if x.strip()}

    print("Nạp pipeline...")
    bot = MedicalChatbot()

    rows = []
    for it in items:
        q = it["question"]
        emb = bot.embedder.encode([f"query: {q}"], normalize_embeddings=True).tolist()
        docs = []
        for col, n in ((bot.encyc, POOL_PER_COLLECTION),
                       (bot.collection, POOL_PER_COLLECTION)):
            if col is not None:
                docs.extend(bot._query(col, emb, n, max_chars=800, is_qa=(col is bot.collection)))
        if not docs:
            continue
        terms = key_terms(it.get("reference_facts", []))
        before = max(docs, key=lambda d: -d["distance"]) if False else min(
            docs, key=lambda d: d["distance"])
        ranked = reranker.rerank(q, docs)
        after = ranked[0]
        rows.append({
            "id": it["id"],
            "type": it.get("type", ""),
            "cov_dense": round(coverage(before["text"], terms), 3),
            "cov_rerank": round(coverage(after["text"], terms), 3),
            "score_rerank": after.get("rerank", 0.0),
            "title_dense": (before.get("question") or "")[:70],
            "title_rerank": (after.get("question") or "")[:70],
            "changed": before.get("question") != after.get("question"),
        })

    n = len(rows)
    imp = [r for r in rows if r["cov_rerank"] > r["cov_dense"] + 0.05]
    wor = [r for r in rows if r["cov_rerank"] < r["cov_dense"] - 0.05]
    print(f"\nSố câu đo: {n}")
    print(f"  độ phủ từ khoá top-1 trung bình: dense {sum(r['cov_dense'] for r in rows)/n:.3f}"
          f"  ->  rerank {sum(r['cov_rerank'] for r in rows)/n:.3f}")
    print(f"  rerank TỐT HƠN rõ rệt: {len(imp)} câu | XẤU HƠN: {len(wor)} câu"
          f" | đổi tài liệu đầu: {sum(r['changed'] for r in rows)} câu")
    print("  id tốt hơn:", ", ".join(r["id"] for r in imp))
    if wor:
        print("  id xấu hơn:", ", ".join(r["id"] for r in wor))

    scores = sorted(r["score_rerank"] for r in rows)
    if scores:
        def pct(p): return scores[min(len(scores) - 1, int(len(scores) * p))]
        print(f"\nPhân bố điểm rerank top-1: min {scores[0]:.3f} "
              f"p10 {pct(0.10):.3f} p50 {pct(0.50):.3f} p90 {pct(0.90):.3f} max {scores[-1]:.3f}")

    for r in rows:
        if r["id"] in show:
            print(f"\n{r['id']} [{r['type']}] phủ {r['cov_dense']:.2f} -> {r['cov_rerank']:.2f}"
                  f" | điểm {r['score_rerank']:.3f}")
            print(f"   dense : {r['title_dense']}")
            print(f"   rerank: {r['title_rerank']}")

    out = SRC / "reranker_probe.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nĐã ghi {out}")


if __name__ == "__main__":
    main()
