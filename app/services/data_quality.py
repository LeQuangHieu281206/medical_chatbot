"""Hàm dùng chung cho chất lượng dữ liệu: chuẩn hoá câu, shingle, phát hiện gần trùng.

Tách ra khỏi `tests/40_data_audit.py` để `scripts/validate_data.py` dùng lại được
mà không phải import từ thư mục tests.
"""
import re
import unicodedata
from collections import Counter, defaultdict

WORD_RE = re.compile(r"\w+", re.UNICODE)

JACCARD_MIN = 0.70   # ngưỡng coi là gần trùng
RARE_SHINGLE = 60    # shingle xuất hiện ở nhiều hơn ngần này câu thì bỏ (quá phổ biến)
SHINGLE_N = 3


def norm(text: str) -> str:
    """Chuẩn hoá để so sánh: NFC, chữ thường, chỉ giữ chữ/số."""
    text = unicodedata.normalize("NFC", text or "").lower()
    return " ".join(WORD_RE.findall(text))


def shingles(text: str, n: int = SHINGLE_N) -> set:
    """Tập shingle n-gram của một câu."""
    toks = norm(text).split()
    if len(toks) < n:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def find_duplicates(rows, key: str = "question"):
    """Gom câu gần trùng bằng shingle + Jaccard, nối nhóm bằng union-find.

    Trả về (dup_groups, pairs): dup_groups là {id gốc: [chỉ số dòng]}, chỉ chứa
    nhóm có từ 2 dòng trở lên.
    """
    sh = [shingles(r.get(key) or "") for r in rows]
    inv = defaultdict(list)
    for i, s in enumerate(sh):
        for g in s:
            inv[g].append(i)

    parent = list(range(len(rows)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    pairs = []
    for i, s in enumerate(sh):
        cand = Counter()
        for g in s:
            ids = inv[g]
            if len(ids) <= RARE_SHINGLE:
                cand.update(ids)
        for j, shared in cand.items():
            if j <= i:
                continue
            denom = len(s) + len(sh[j]) - shared
            if denom and shared / denom >= JACCARD_MIN:
                union(i, j)
                pairs.append((i, j, shared / denom))

    groups = defaultdict(list)
    for i in range(len(rows)):
        groups[find(i)].append(i)
    return {k: v for k, v in groups.items() if len(v) > 1}, pairs


def pick_keeper(rows, ids):
    """Giữ dòng có nguồn (link) và đáp án dài nhất; các dòng còn lại là bản trùng."""
    return max(ids, key=lambda i: (
        bool((rows[i].get("link") or "").strip()),
        len(rows[i].get("answer") or ""),
    ))
