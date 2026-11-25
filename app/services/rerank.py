"""Xếp lại kết quả truy hồi bằng tín hiệu từ vựng — không cần model thêm.

Vì sao cần: đo trên 500 câu eval cho thấy khoảng cách top-1 trung bình chỉ 0,085
(rất gần) nhưng Recall@3 chỉ ~12%. Nghĩa là ChromaDB lấy về tài liệu **cùng chủ đề
nhưng không đúng câu hỏi**, và LLM nhận ngữ cảnh na ná rồi tự suy ra — nguồn của
26% câu trả lời có thông tin bịa.

Cách làm: lấy nhiều ứng viên (top-N), rồi tính lại điểm bằng ba tín hiệu rẻ tiền:

1. `1 - distance`  — độ gần ngữ nghĩa của embedding (đã có sẵn, không tính lại).
2. Dice trên token giữa câu hỏi người dùng và **câu hỏi của tài liệu** — tài liệu
   KB là cặp hỏi-đáp nên đây là tín hiệu mạnh nhất.
3. Dice trên token với phần đầu đáp án — bắt các trường hợp tên bệnh/thuốc trùng
   nhưng câu hỏi viết khác.

Không dùng cross-encoder vì phải thêm model ~100 MB và chậm gấp nhiều lần; ba tín
hiệu trên đã đủ tách đúng câu hỏi khỏi "cùng chủ đề".

Chạy thử:
    .venv/bin/python -m app.services.rerank "tiêm 6in1 trễ có sao không"
"""
import re
import sys
import unicodedata

# Trọng số chọn bằng quét trên 500 câu eval (xem scripts/eval_kb_recall.py --rerank-top)
W_DIST, W_QUESTION, W_TEXT = 0.45, 0.45, 0.10

_STOP = frozenset(
    "là gì có không nên khi nào như thế nào và của cho với thì mà ở ra vào "
    "tôi bạn em mình bị được các những một hai ba người bệnh".split()
)


def tokens(s: str) -> set:
    """Token đã bỏ dấu, bỏ từ dừng — để "tiêm chủng" khớp "tiem chung"."""
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d")
    return {w for w in re.findall(r"[a-z0-9]+", s) if len(w) > 1 and w not in _STOP}


def dice(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def score(query: str, doc_question: str, doc_text: str, distance: float) -> float:
    """Điểm càng cao càng tốt. `distance` là khoảng cách cosine của ChromaDB."""
    qt = tokens(query)
    return (W_DIST * (1.0 - distance)
            + W_QUESTION * dice(qt, tokens(doc_question))
            + W_TEXT * dice(qt, tokens((doc_text or "")[:500])))


def rerank(query: str, docs: list, metas: list, dists: list, k: int) -> list:
    """docs/metas/dists là kết quả thô của ChromaDB; trả về k chỉ số tốt nhất."""
    scored = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
        q = (meta or {}).get("question", "")
        scored.append((score(query, q, doc, dist), i))
    scored.sort(reverse=True)
    return [i for _, i in scored[:k]]


def _main():
    import chromadb
    from sentence_transformers import SentenceTransformer

    from app.services.topic_filter import COLLECTION, DB_PATH, EMBED_MODEL

    q = " ".join(sys.argv[1:]) or "tiêm 6in1 trễ có sao không"
    model = SentenceTransformer(EMBED_MODEL)
    col = chromadb.PersistentClient(path=DB_PATH).get_collection(COLLECTION)
    emb = model.encode([f"query: {q}"], normalize_embeddings=True)[0].tolist()
    res = col.query(query_embeddings=[emb], n_results=12,
                    include=["documents", "metadatas", "distances"])
    docs, metas, dists = res["documents"][0], res["metadatas"][0], res["distances"][0]
    order = rerank(q, docs, metas, dists, k=3)
    print(f"Q: {q}\n")
    for rank, i in enumerate(order, 1):
        s = score(q, (metas[i] or {}).get("question", ""), docs[i], dists[i])
        print(f"{rank}. điểm {s:.3f} (cách {dists[i]:.3f}) | {(metas[i] or {}).get('question','')[:90]}")


if __name__ == "__main__":
    _main()
