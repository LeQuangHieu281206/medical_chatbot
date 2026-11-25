"""Nạp KB đã tách chunk (data/processed/kb_chunked.jsonl) vào collection MỚI medical_kb_v2.

Không xoá collection cũ medical_kb — chạy song song để so sánh trước khi đổi.

Chạy: .venv/bin/python app/services/ingest_kb_v2.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from app.services.topic_filter import DB_PATH, EMBED_MODEL

SRC = Path("data/processed/kb_chunked.jsonl")
NEW_COLLECTION = "medical_kb_v2"
BATCH = 64


def embed_text(r: dict) -> str:
    """Chuỗi đem đi embed: có tiêu đề mục để câu "X là gì" khớp đúng đoạn định nghĩa."""
    head = f"{r['question']}"
    if r.get("section"):
        head += f" — {r['section'][:60]}"
    return f"passage: {head}\n{r['text']}"


def doc_text(r: dict) -> str:
    """Chuỗi hiển thị/đưa vào prompt; giữ dạng 'Hỏi:/Đáp:' để pipeline._qa_text cắt được."""
    return f"Hỏi: {r['question']}\nĐáp: {r['text']}"


def main():
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    print(f"Đọc {len(rows)} chunk từ {SRC}")
    if not rows:
        print("File rỗng, dừng.")
        return

    model = SentenceTransformer(EMBED_MODEL)
    model.max_seq_length = 512

    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(NEW_COLLECTION)
        print(f"Đã xoá collection cũ {NEW_COLLECTION} (nếu có)")
    except Exception:
        pass
    col = client.create_collection(NEW_COLLECTION, metadata={"hnsw:space": "cosine"})

    t0 = time.perf_counter()
    for i in tqdm(range(0, len(rows), BATCH), desc="Nạp medical_kb_v2"):
        batch = rows[i:i + BATCH]
        embs = model.encode([embed_text(r) for r in batch], batch_size=BATCH,
                            normalize_embeddings=True, show_progress_bar=False).tolist()
        col.add(
            ids=[f"kb2_{r['parent_id']}_{j}" for j, r in enumerate(batch)],
            embeddings=embs,
            documents=[doc_text(r) for r in batch],
            metadatas=[{
                "source": r["source"],
                "question": r["question"],
                "link": r.get("link", ""),
                "section": r.get("section", "") or "",
                "parent_id": int(r["parent_id"]),
            } for r in batch],
        )
    elapsed = time.perf_counter() - t0
    print(f"\n{ NEW_COLLECTION }: {col.count()} document | {elapsed:.0f}s "
          f"({len(rows) / elapsed:.1f} chunk/s)")

    old = client.get_collection("medical_kb")
    print(f"medical_kb (cũ, không đổi): {old.count()} document")


if __name__ == "__main__":
    main()
