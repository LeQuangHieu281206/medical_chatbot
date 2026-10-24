from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

DATA_DIR = Path("data/raw")
DB_DIR = "app/db/chroma_db"
COLLECTION = "medical_kb"
EMBED_MODEL = "intfloat/multilingual-e5-small"
CHUNK_SIZE = 800   # số ký tự tối đa mỗi đoạn
OVERLAP = 100      # chỉ dùng khi một đoạn văn dài hơn CHUNK_SIZE


def split_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    """Gộp các đoạn văn liền kề cho đến khi gần đủ size."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) + 2 <= size:
            current = f"{current}\n\n{p}" if current else p
        else:
            if current:
                chunks.append(current)
            while len(p) > size:
                chunks.append(p[:size])
                p = p[size - overlap:]
            current = p
    if current:
        chunks.append(current)
    return chunks


def main():
    files = sorted(list(DATA_DIR.glob("*.txt")) + list(DATA_DIR.glob("*.md")))
    if not files:
        print("Không tìm thấy file .txt hoặc .md trong thư mục data/")
        return

    documents, ids, metadatas = [], [], []
    for f in files:
        chunks = split_text(f.read_text(encoding="utf-8"))
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            ids.append(f"{f.stem}-{i}")
            metadatas.append({"source": f.name, "chunk": i})
        print(f"{f.name}: {len(chunks)} đoạn")

    print("Đang nạp model embedding (lần đầu sẽ tải về khoảng 470 MB)...")
    model = SentenceTransformer(EMBED_MODEL)
    # model e5 yêu cầu tiền tố "passage: " cho tài liệu
    embeddings = model.encode(
        [f"passage: {d}" for d in documents],
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    client = chromadb.PersistentClient(path=DB_DIR)
    # xoá collection cũ để chạy lại ingest không bị trùng
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    print(f"Xong. Đã lưu {collection.count()} đoạn vào {DB_DIR}/")


if __name__ == "__main__":
    main()