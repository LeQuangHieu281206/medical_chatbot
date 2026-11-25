"""Đo Recall@k của collection QA trên bộ eval (câu hỏi thật của người bệnh).

Dùng để so hai collection trước/sau khi thêm dữ liệu — cùng câu hỏi, cùng model
embedding, chỉ khác dữ liệu. Không gọi LLM nên chạy được khi Ollama tắt.

Chạy:
    .venv/bin/python scripts/eval_kb_recall.py                      # so medical_kb với kb.jsonl
    .venv/bin/python scripts/eval_kb_recall.py --collections medical_kb medical_kb_v3
    .venv/bin/python scripts/eval_kb_recall.py --n 1000 --k 5
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import chromadb  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.services.data_quality import norm  # noqa: E402
from app.services.topic_taxonomy import tag_topic  # noqa: E402
from app.services import rerank as rr  # noqa: E402

DB_PATH = ROOT / "app/db/chroma_db"
EMBED_MODEL = "intfloat/multilingual-e5-small"
EVAL = ROOT / "data/processed/eval.jsonl"
MIN_GOLD = 60      # đáp án chuẩn ngắn hơn ngần này thì bỏ khỏi phép đo
KB = ROOT / "data/processed/kb.jsonl"


def main():
    ap = argparse.ArgumentParser(description="Recall@k của collection QA trên bộ eval")
    ap.add_argument("--collections", nargs="+", default=["medical_kb"])
    ap.add_argument("--n", type=int, default=500, help="số câu eval dùng để đo")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rerank-top", type=int, metavar="N",
                    help="lấy N ứng viên rồi xếp lại bằng app/services/rerank.py")
    ap.add_argument("--topics", nargs="+",
                    help="chỉ đo trên các chủ đề này (vd: vaccine dinh-duong)")
    args = ap.parse_args()

    eval_rows = [json.loads(l) for l in EVAL.open(encoding="utf-8") if l.strip()]
    if args.topics:
        keep = set(args.topics)
        eval_rows = [r for r in eval_rows
                     if tag_topic(r["question"], r["answer"]) in keep]
        print(f"lọc chủ đề {sorted(keep)}: còn {len(eval_rows)} câu")
    kb_rows = [json.loads(l) for l in KB.open(encoding="utf-8") if l.strip()]
    kb_questions = {norm(r["question"]) for r in kb_rows}
    overlap = sum(1 for r in eval_rows if norm(r["question"]) in kb_questions)
    random.seed(args.seed)
    sample = random.sample(eval_rows, min(args.n, len(eval_rows)))
    print(f"eval: {len(eval_rows)} câu | trùng câu hỏi với kb.jsonl: {overlap} "
          f"| đo trên {len(sample)} câu")
    print("khớp tính theo đáp án: đáp án chuẩn phải nằm trong tài liệu truy hồi")

    model = SentenceTransformer(EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(DB_PATH))
    embs = model.encode([f"query: {r['question']}" for r in sample],
                        batch_size=32, normalize_embeddings=True,
                        show_progress_bar=False).tolist()

    report = {}
    for name in args.collections:
        try:
            col = client.get_collection(name)
        except Exception:  # noqa: BLE001
            print(f"\n{name}: không có collection này — bỏ qua")
            continue
        hits1 = hits_k = unusable = 0
        t0 = time.time()
        fetch = max(args.k, args.rerank_top or args.k)
        for i in range(0, len(sample), 50):
            res = col.query(query_embeddings=embs[i:i + 50], n_results=fetch,
                            include=["documents", "metadatas", "distances"]
                            if args.rerank_top else ["documents"])
            for row_i, (gold, docs) in enumerate(zip(sample[i:i + 50], res["documents"])):
                if args.rerank_top:
                    metas = res["metadatas"][row_i]
                    dists = res["distances"][row_i]
                    order = rr.rerank(gold["question"], docs, metas, dists, args.k)
                    docs = [docs[j] for j in order]
                else:
                    docs = docs[:args.k]
                g = norm(gold["answer"])
                if len(g) < MIN_GOLD:      # đáp án chuẩn quá ngắn: containment vô nghĩa
                    unusable += 1
                    continue
                got = [norm(d) for d in docs]
                if got and g in got[0]:
                    hits1 += 1
                if any(g in d for d in got):
                    hits_k += 1
        n = len(sample) - unusable
        if n <= 0:
            print(f"\n{name}: không có câu nào đo được")
            continue
        report[name] = (hits1 / n, hits_k / n, col.count(), n)
        print(f"\n{name} ({col.count()} document, {n} câu đo được)")
        print(f"  Recall@1: {100 * hits1 / n:.1f}%")
        print(f"  Recall@{args.k}: {100 * hits_k / n:.1f}%")
        print(f"  thời gian truy vấn: {time.time() - t0:.0f}s")

    if len(report) > 1:
        names = list(report)
        base = report[names[0]]
        print(f"\nSo với {names[0]}:")
        for name in names[1:]:
            r = report[name]
            print(f"  {name}: Recall@1 {100 * (r[0] - base[0]):+.1f} điểm, "
                  f"Recall@{args.k} {100 * (r[1] - base[1]):+.1f} điểm")


if __name__ == "__main__":
    main()
