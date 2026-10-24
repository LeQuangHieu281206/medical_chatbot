import sys

import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")
collection = chromadb.PersistentClient(path="app/db/chroma_db").get_collection("medical_kb")

query = " ".join(sys.argv[1:]) or "Khi nào cần đi khám khi bị cúm?"
# model e5 yêu cầu tiền tố "query: " cho câu hỏi
q_emb = model.encode([f"query: {query}"], normalize_embeddings=True).tolist()

result = collection.query(query_embeddings=q_emb, n_results=3)

print(f"Câu hỏi: {query}\n")
for doc, meta, dist in zip(
    result["documents"][0], result["metadatas"][0], result["distances"][0]
):
    print(f"[khoảng cách {dist:.3f}] {meta['source']} (đoạn {meta['chunk']})")
    print(doc[:200].replace("\n", " "), "...\n")