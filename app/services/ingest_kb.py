"""Nạp KB hỏi đáp vào một collection ChromaDB.

Mặc định giữ nguyên hành vi cũ: `data/processed/kb.jsonl` → collection `medical_kb`
(có xoá collection trước khi nạp). Để so sánh trước/sau, nạp sang collection mới
rồi mới đổi hằng số trong `app/services/topic_filter.py`:

    # nạp KB gộp (thường + thuốc) sang collection mới, không chạm collection đang chạy
    .venv/bin/python app/services/ingest_kb.py \
        --kb data/processed/kb_merged.jsonl --collection medical_kb_v3

Chạy:
    .venv/bin/python app/services/ingest_kb.py                  # như cũ
    .venv/bin/python app/services/ingest_kb.py --help
"""
import argparse
import json
import time
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

DEFAULT_KB = Path("data/processed/kb.jsonl")
DB_PATH = "app/db/chroma_db"
DEFAULT_COLLECTION = "medical_kb"
MODEL_NAME = "intfloat/multilingual-e5-small"
BATCH = 64


def main():
    ap = argparse.ArgumentParser(description="Nạp KB hỏi đáp vào ChromaDB")
    ap.add_argument("--kb", default=str(DEFAULT_KB), help="file JSONL đầu vào")
    ap.add_argument("--collection", default=DEFAULT_COLLECTION)
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--no-smoke-test", action="store_true",
                    help="bỏ 4 câu kiểm tra nhanh sau khi nạp")
    ap.add_argument("--append", action="store_true",
                    help="thêm vào collection đang có thay vì xoá và nạp lại toàn bộ (upsert id theo tên file)")
    args = ap.parse_args()

    kb_path = Path(args.kb)
    rows = [json.loads(line) for line in kb_path.open(encoding="utf-8") if line.strip()]
    print(f"{kb_path}: {len(rows)} bản ghi → collection '{args.collection}'", flush=True)

    model = SentenceTransformer(MODEL_NAME)
    model.max_seq_length = 512

    client = chromadb.PersistentClient(path=args.db)
    if args.append:
        col = client.get_or_create_collection(args.collection, metadata={"hnsw:space": "cosine"})
        print(f"Thêm vào collection '{args.collection}' (đang có {col.count()} document)", flush=True)
    else:
        try:
            client.delete_collection(args.collection)
            print(f"Đã xoá collection cũ '{args.collection}'", flush=True)
        except Exception:  # noqa: BLE001 - collection chưa có là bình thường
            pass
        col = client.create_collection(args.collection, metadata={"hnsw:space": "cosine"})

    id_prefix = kb_path.stem      # append: id theo tên file, không đạp lên id cũ
    t0 = time.time()
    for i in tqdm(range(0, len(rows), args.batch), desc="Nạp dữ liệu"):
        batch = rows[i:i + args.batch]
        texts = [f"passage: {r['question']}\n{r['answer']}" for r in batch]
        embs = model.encode(texts, normalize_embeddings=True, batch_size=args.batch).tolist()
        ids = ([f"kb_{i + j}" for j in range(len(batch))] if not args.append
               else [f"{id_prefix}-{i + j}" for j in range(len(batch))])
        write = col.upsert if args.append else col.add
        write(
            ids=ids,
            embeddings=embs,
            documents=[f"Hỏi: {r['question']}\nĐáp: {r['answer']}" for r in batch],
            metadatas=[
                {"source": r["source"], "question": r["question"], "link": r.get("link", "")}
                for r in batch
            ],
        )

    print(f"\nXong sau {time.time() - t0:.0f}s. Tổng document trong DB: {col.count()}", flush=True)

    if args.no_smoke_test:
        return
    tests = [
        "Khi nào cần đi khám khi bị cúm?",
        "Trẻ bị sốt cao co giật thì xử lý thế nào?",
        "Paracetamol tương tác với thuốc nào?",
        "Công thức nấu phở bò",
        "Giá bitcoin hôm nay bao nhiêu?",
    ]
    for q in tests:
        qe = model.encode([f"query: {q}"], normalize_embeddings=True).tolist()
        res = col.query(query_embeddings=qe, n_results=3)
        print("\nQ:", q, flush=True)
        for d, m in zip(res["distances"][0], res["metadatas"][0]):
            print(f"  {d:.3f} | {m['source'][:18]:<18} | {m['question'][:70]}", flush=True)


if __name__ == "__main__":
    main()
