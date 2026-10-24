import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

KB_PATH = Path("data/processed/kb.jsonl")
DB_PATH = "app/db/chroma_db"
COLLECTION = "medical_kb"
MODEL_NAME = "intfloat/multilingual-e5-small"
BATCH = 64

with open(KB_PATH, encoding="utf-8") as f:
    rows = [json.loads(line) for line in f]
print("Số bản ghi:", len(rows))

model = SentenceTransformer(MODEL_NAME)
model.max_seq_length = 512

client = chromadb.PersistentClient(path=DB_PATH)
try:
    client.delete_collection(COLLECTION)  # xoá collection cũ (chỉ có đoạn mẫu cúm)
except Exception:
    pass
col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

for i in tqdm(range(0, len(rows), BATCH), desc="Nạp dữ liệu"):
    batch = rows[i : i + BATCH]
    texts = [f"passage: {r['question']}\n{r['answer']}" for r in batch]
    embs = model.encode(texts, normalize_embeddings=True, batch_size=BATCH).tolist()
    col.add(
        ids=[f"kb_{i + j}" for j in range(len(batch))],
        embeddings=embs,
        documents=[f"Hỏi: {r['question']}\nĐáp: {r['answer']}" for r in batch],
        metadatas=[
            {"source": r["source"], "question": r["question"], "link": r["link"]}
            for r in batch
        ],
    )

print("Tổng số document trong DB:", col.count())

# Kiểm tra nhanh: 2 câu y tế, 2 câu ngoài chủ đề
tests = [
    "Khi nào cần đi khám khi bị cúm?",
    "Trẻ bị sốt cao co giật thì xử lý thế nào?",
    "Công thức nấu phở bò",
    "Giá bitcoin hôm nay bao nhiêu?",
]
for q in tests:
    qe = model.encode([f"query: {q}"], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=qe, n_results=3)
    print("\nQ:", q)
    for d, m in zip(res["distances"][0], res["metadatas"][0]):
        print(f"  {d:.3f} | {m['question'][:80]}")