"""Đo chất lượng truy hồi bằng độ tương đồng ngữ nghĩa của ĐÁP ÁN.

Vì sao cần: `scripts/eval_kb_recall.py` tính "đáp án chuẩn nằm nguyên văn trong tài
liệu truy hồi". Với ViHealthQA, mỗi câu hỏi có một đáp án dài khác nhau, nên phép đo
này chỉ đạt ~12% kể cả khi truy hồi đúng chủ đề — nó đo *trùng chữ*, không đo *đúng ý*.
Đã thử nâng recall bằng hai cách (xếp lại bằng từ vựng, và fuse TF-IDF với dense):
cả hai đều **không tăng**, vì trần của phép đo chỉ ~13%. Nghĩa là muốn biết truy hồi
tốt hay kém thì phải đổi thước đo.

Cách đo ở đây: lấy đáp án chuẩn của câu eval, so cosine với 3 đáp án được truy hồi —
đúng ý thì cosine cao dù câu chữ khác.

Chạy:
    .venv/bin/python scripts/eval_retrieval_semantic.py
    .venv/bin/python scripts/eval_retrieval_semantic.py --collections medical_kb medical_kb_v3
    .venv/bin/python scripts/eval_retrieval_semantic.py --topics vaccine dinh-duong --n 200
"""
import argparse
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import chromadb  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.services.topic_taxonomy import tag_topic  # noqa: E402

DB_PATH = ROOT / "app/db/chroma_db"
EMBED_MODEL = "intfloat/multilingual-e5-small"
EVAL = ROOT / "data/processed/eval.jsonl"
MIN_GOLD = 60          # đáp án chuẩn ngắn hơn thì bỏ
GOOD = 0.88            # cosine được coi là "đúng ý" (hiệu chỉnh theo dữ liệu ở dưới)


def main():
    ap = argparse.ArgumentParser(description="Recall theo ngữ nghĩa của đáp án")
    ap.add_argument("--collections", nargs="+", default=["medical_kb_v3"])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--topics", nargs="+")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--good", type=float, default=GOOD,
                    help="ngưỡng cosine coi là đúng ý (mặc định 0.88)")
    args = ap.parse_args()

    rows = [json.loads(l) for l in EVAL.open(encoding="utf-8") if l.strip()]
    if args.topics:
        keep = set(args.topics)
        rows = [r for r in rows if tag_topic(r["question"], r["answer"]) in keep]
        print(f"lọc chủ đề {sorted(keep)}: {len(rows)} câu")
    rows = [r for r in rows if len(r["answer"]) >= MIN_GOLD]
    random.seed(args.seed)
    sample = random.sample(rows, min(args.n, len(rows)))
    print(f"đo trên {len(sample)} câu eval | ngưỡng đúng ý = {args.good}")

    model = SentenceTransformer(EMBED_MODEL)
    q_emb = model.encode([f"query: {r['question']}" for r in sample],
                         normalize_embeddings=True, show_progress_bar=False)
    gold_emb = model.encode([f"passage: {r['answer']}" for r in sample],
                            normalize_embeddings=True, show_progress_bar=False)

    client = chromadb.PersistentClient(path=str(DB_PATH))
    for name in args.collections:
        try:
            col = client.get_collection(name)
        except Exception:  # noqa: BLE001
            print(f"\n{name}: không có collection này — bỏ qua")
            continue

        res = col.query(query_embeddings=q_emb.tolist(), n_results=args.k,
                        include=["documents", "metadatas", "distances"])
        cands = []
        for docs, metas in zip(res["documents"], res["metadatas"]):
            cands.append([f"passage: {(m or {}).get('question', '')}\n{d}"
                          for d, m in zip(docs, metas)])
        flat = model.encode([c for row in cands for c in row],
                            normalize_embeddings=True, show_progress_bar=False)

        hit1 = hitk = 0
        sims = []
        for i in range(len(sample)):
            chunk = flat[i * args.k:(i + 1) * args.k]
            s = (chunk @ gold_emb[i]).tolist()
            sims += s
            if s and s[0] >= args.good:
                hit1 += 1
            if any(x >= args.good for x in s):
                hitk += 1
        n = len(sample)
        print(f"\n{name} ({col.count()} document)")
        print(f"  Đúng ý @1: {100 * hit1 / n:.1f}%")
        print(f"  Đúng ý @{args.k}: {100 * hitk / n:.1f}%")
        print(f"  cosine đáp án top-1: trung bình {statistics.mean(sims[::args.k]):.3f} | "
              f"trung vị {statistics.median(sims[::args.k]):.3f}")


if __name__ == "__main__":
    main()
