"""Truy xuất lai (hybrid): dense + BM25, gộp thứ hạng bằng RRF.

Vì sao cần: đo bằng ``tests/56_doc_recall.py`` trên 19 câu từng trả lời sai —
bài đúng chủ đề (khớp tiêu đề) có trong 50 tài liệu gần nhất của dense ở 16/19
câu, nhưng chỉ **5/19** vào được ngữ cảnh, vì phần lớn nằm ở hạng 4–27 còn
pipeline chỉ lấy 1 bài hỏi đáp.

Chiến lược ở đây:

1. Lấy bể ứng viên rộng bằng dense (``POOL`` mỗi collection) — giữ nguyên chất
   lượng của embedding, không cần index toàn kho.
2. Tính thêm BM25 tại chỗ trên chính bể đó: bắt các từ khoá hiếm mà vector bỏ
   sót ("chiều cao giảm", "gút", "tiểu đêm").
3. Gộp hai thứ hạng bằng Reciprocal Rank Fusion, rồi mới cắt theo quota.

RRF dùng THỨ HẠNG nên tránh được lỗi so sánh hai loại điểm khác đơn vị (khoảng
cách cosine và điểm BM25). Đo được +2 câu vào top-3 so với dense thuần trên 15
câu — nhỏ, nhưng cái đáng giá hơn là **bể rộng**: đó là phần kéo recall từ
5/19 lên.
"""

from __future__ import annotations

import math
import re

RRF_K = 60
BM25_K1 = 1.5
BM25_B = 0.75
POOL = 20           # số ứng viên dense lấy mỗi collection trước khi gộp

WORD = re.compile(r"[0-9a-zA-ZÀ-ỹ]+")


def tokenize(text: str) -> list[str]:
    return WORD.findall((text or "").lower())


def bm25_scores(query: str, docs: list[str]) -> list[float]:
    """BM25 tính tại chỗ trên bể ứng viên (không cần xây index)."""
    qtok = tokenize(query)
    toks = [tokenize(d) for d in docs]
    n = len(toks)
    if not n or not qtok:
        return [0.0] * n
    avgdl = sum(len(t) for t in toks) / n or 1.0
    df: dict[str, int] = {}
    for t in toks:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    out = []
    for t in toks:
        tf: dict[str, int] = {}
        for w in t:
            tf[w] = tf.get(w, 0) + 1
        dl = len(t) or 1
        s = 0.0
        for w in qtok:
            f = tf.get(w)
            if not f:
                continue
            idf = math.log(1 + (n - df.get(w, 0) + 0.5) / (df.get(w, 0) + 0.5))
            s += idf * (f * (BM25_K1 + 1)) / (f + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl))
        out.append(s)
    return out


def _dense_ranks(distances: list[float]) -> list[int]:
    order = sorted(range(len(distances)), key=lambda i: distances[i])
    ranks = [0] * len(distances)
    for pos, idx in enumerate(order, 1):
        ranks[idx] = pos
    return ranks


def fuse(query: str, docs: list[str], distances: list[float],
         k: int = RRF_K) -> list[int]:
    """Trả về thứ tự chỉ số tài liệu sau khi gộp dense + BM25."""
    dense = _dense_ranks(distances)
    bm = bm25_scores(query, docs)
    order = sorted(range(len(bm)), key=lambda i: -bm[i])
    bm_rank = [0] * len(bm)
    for pos, idx in enumerate(order, 1):
        bm_rank[idx] = pos
    score = [1.0 / (k + dense[i]) + 1.0 / (k + bm_rank[i]) for i in range(len(docs))]
    return sorted(range(len(docs)), key=lambda i: -score[i])
