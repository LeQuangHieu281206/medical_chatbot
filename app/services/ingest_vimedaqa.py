import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import chromadb
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from app.services.topic_filter import COLLECTION, DB_PATH, EMBED_MODEL

NEW_COLLECTION = f"{COLLECTION}_vimedaqa"
BATCH = 128
TOPIC = {"0": "body-part", "1": "disease", "2": "drug", "3": "medicine"}
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else None

print("Đang tải bộ dữ liệu (cấu hình all)...")
ds = load_dataset("tmnam20/ViMedAQA", "all")

seen, rows = set(), []
for split in ds:
    for r in ds[split]:
        ctx = (r["context"] or "").strip()
        if len(ctx) < 40:
            continue
        key = (r["article_url"], ctx)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "id": "vm_" + hashlib.sha1(f"{r['article_url']}|{ctx}".encode("utf-8")).hexdigest()[:16],
            "title": (r["title"] or "").strip(),
            "keyword": (r["keyword"] or "").strip(),
            "context": ctx,
            "url": r["article_url"] or "",
            "topic": TOPIC.get(str(r["topic"]), "unknown"),
        })

print(f"Đoạn văn duy nhất sau khi khử trùng lặp: {len(rows)}")
if LIMIT:
    rows = rows[:LIMIT]
    print(f"Chế độ chạy thử: chỉ nạp {len(rows)} đoạn")

model = SentenceTransformer(EMBED_MODEL)
client = chromadb.PersistentClient(path=DB_PATH)
try:
    client.delete_collection(NEW_COLLECTION)
except Exception:
    pass
col = client.create_collection(NEW_COLLECTION, metadata={"hnsw:space": "cosine"})

t0 = time.perf_counter()
for i in tqdm(range(0, len(rows), BATCH), desc="Nạp ViMedAQA"):
    batch = rows[i : i + BATCH]
    texts = [f"passage: {r['keyword']} - {r['title']}\n{r['context']}" for r in batch]
    embs = model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()
    col.add(
        ids=[r["id"] for r in batch],
        embeddings=embs,
        documents=[f"{r['keyword']} - {r['title']}\n{r['context']}" for r in batch],
        metadatas=[
            {"source": "ViMedAQA", "question": r["title"] or r["keyword"],
             "link": r["url"], "topic": r["topic"], "keyword": r["keyword"]}
            for r in batch
        ],
    )
elapsed = time.perf_counter() - t0
rate = len(rows) / elapsed
print(f"\nTổng document trong {NEW_COLLECTION}: {col.count()}")
print(f"Tốc độ: {rate:.1f} đoạn/giây; nạp {len(rows)} đoạn mất {elapsed:.0f} s")
if LIMIT:
    print(f"Ước tính nạp toàn bộ: khoảng {(2 * 1e4) / rate / 60:.0f} phút cho mỗi 20.000 đoạn")

# Kiểm tra nhanh bằng vài câu hỏi
for q in ["Khi nào cần đi khám khi bị cúm?", "Bệnh cúm là gì?", "Paracetamol là thuốc gì?"]:
    qe = model.encode([f"query: {q}"], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=qe, n_results=3, include=["metadatas", "distances"])
    print("\nHỏi:", q)
    for m, d in zip(res["metadatas"][0], res["distances"][0]):
        print(f"  d={d:.3f} | {m['topic']:9s} | {m['question'][:70]}")