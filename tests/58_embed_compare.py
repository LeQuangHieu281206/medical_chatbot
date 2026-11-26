"""So sánh embedding model ở mức TIÊU ĐỀ bài viết (rất nhẹ, không cần nạp lại KB).

Bài toán cần giải: câu hỏi chỉ mô tả triệu chứng ("khát nước, tiểu đêm, sụt 4kg")
phải tìm ra bài có tiêu đề tên bệnh ("Đái tháo đường"). Đo bằng cách:

1. Lấy tiêu đề mọi bài trong collection (metadata ``question``) — chuỗi ngắn.
2. Embed tiêu đề + câu hỏi bằng từng model.
3. Xem câu hỏi có kéo được bài ĐÚNG CHỦ ĐỀ vào top-3 / top-10 không.

So sánh tương đối giữa các model là đáng tin vì cùng một bộ tiêu đề, cùng câu hỏi.
Sau khi chọn được model, mới phải nạp lại toàn bộ KB (tốn vài giờ trên CPU).

Cách chạy::

    .venv/bin/python tests/58_embed_compare.py
    .venv/bin/python tests/58_embed_compare.py --models A B
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _recall_patterns import PATTERNS  # noqa: E402

SRC = ROOT / "data" / "sources"
EVAL = SRC / "eval_answers_50.jsonl"
OUT = SRC / "embed_compare.json"

DEFAULT_MODELS = [
    "intfloat/multilingual-e5-small",
    "keepitreal/vietnamese-sbert",
    "dangvantuan/vietnamese-embedding",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--collection", default="medical_kb_v3")
    ap.add_argument("--top", type=int, nargs="*", default=[3, 10])
    ap.add_argument("--sample", type=int, default=0,
                    help="chỉ dùng N tiêu đề ngẫu nhiên (giữ toàn bộ tiêu đề khớp bệnh); "
                         "0 = dùng hết. Dùng khi máy thiếu RAM.")
    args = ap.parse_args()

    import chromadb
    from sentence_transformers import SentenceTransformer
    from app.services.topic_filter import DB_PATH

    col = chromadb.PersistentClient(path=DB_PATH).get_collection(args.collection)
    metas = col.get(include=["metadatas"], limit=100000)["metadatas"]
    titles, seen = [], set()
    for m in metas:
        t = ((m or {}).get("question") or "").strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            titles.append(t)
    if args.sample and args.sample < len(titles):
        import random
        random.seed(0)
        keep = [t for t in titles if any(re.search(p, t, re.I) for p in PATTERNS.values())]
        rest = [t for t in titles if t not in set(keep)]
        titles = keep + random.sample(rest, max(0, args.sample - len(keep)))
    print(f"Tiêu đề dùng để đo: {len(titles):,} (collection {args.collection})")

    ev = {json.loads(l)["id"]: json.loads(l)
          for l in open(EVAL, encoding="utf-8") if l.strip()}
    qids = [q for q in PATTERNS if q in ev]
    questions = [ev[q]["question"] for q in qids]

    results = {}
    for name in args.models:
        try:
            t0 = time.time()
            model = SentenceTransformer(name)
        except Exception as exc:
            print(f"\n{name}: KHÔNG nạp được ({type(exc).__name__}: {str(exc)[:100]})")
            results[name] = {"error": str(exc)[:200]}
            continue
        # PhoBERT (RoBERTa) giới hạn 258 vị trí; tiêu đề hỏi đáp có thể dài hơn
        # -> phải cắt, nếu không sẽ lỗi "index out of bounds for dimension 1".
        try:
            model.max_seq_length = min(int(model.max_seq_length or 512), 256)
        except Exception:
            pass
        titles = [t[:600] for t in titles]
        dim = model.get_sentence_embedding_dimension()
        pref = "query: " if "e5" in name.lower() else ""
        emb_t = model.encode(titles, normalize_embeddings=True,
                             batch_size=64, show_progress_bar=False)
        emb_q = model.encode([pref + q for q in questions],
                             normalize_embeddings=True, show_progress_bar=False)
        sims = emb_q @ emb_t.T                     # (n_câu, n_tiêu đề)
        dt = time.time() - t0
        del model

        line = {}
        for top in args.top:
            hits = 0
            miss = []
            for i, qid in enumerate(qids):
                pat = PATTERNS[qid]
                order = sims[i].argsort()[::-1][:top]
                ok = any(re.search(pat, titles[j], re.I) for j in order)
                hits += ok
                if not ok:
                    miss.append(qid)
            line[f"top{top}"] = {"hits": hits, "miss": miss}
        line["dim"] = int(dim)
        line["seconds"] = round(dt, 1)
        results[name] = line
        parts = " ".join(f"top{t}: {line[f'top{t}']['hits']}/{len(qids)}" for t in args.top)
        print(f"{name:<36} dim={dim:<5} {parts}  ({dt:.0f}s)")
        print(f"{'':<36} thiếu top3: {' '.join(line[f'top{args.top[0]}']['miss']) or '-'}")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nĐã ghi {OUT}")


if __name__ == "__main__":
    main()
