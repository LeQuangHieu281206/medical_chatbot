"""Kiểm tra câu trả lời có bám vào ngữ cảnh truy hồi hay không.

Vì sao cần: bộ chấm 50 câu cho thấy 68% trả lời đúng nhưng **26% có thông tin bịa**.
Đo lại truy hồi bằng thước đo ngữ nghĩa (`scripts/eval_retrieval_semantic.py`) thì
truy hồi đúng ý 73% ở top-1 và 86% ở top-3 — tức là ngữ cảnh nhìn chung vẫn tới nơi.
Vậy chỗ sinh ra thông tin bịa là bước viết câu trả lời: mô hình thêm chi tiết không
có trong ngữ cảnh (liều, thời gian, tên thuốc, con số).

Cách chặn rẻ nhất, không cần model thêm: tách câu trả lời thành từng câu, đo độ trùng
từ vựng với ngữ cảnh; câu nào không bám vào ngữ cảnh thì bỏ. Nếu quá nửa số câu bị bỏ
thì coi như không có ngữ cảnh và trả lời từ chối.

Không dùng cách này để *thêm* thông tin, chỉ để *bỏ* câu không có căn cứ.
"""
import re
import unicodedata

MIN_SUPPORT = 0.70      # tỉ lệ token của câu được ngữ cảnh bao phủ
MIN_KEEP = 0.50         # giữ được dưới nửa số câu thì coi như không có ngữ cảnh

_STOP = frozenset(
    "là gì có không nên khi nào như thế nào và của cho với thì mà ở ra vào "
    "tôi bạn em mình bị được các những một hai ba người bệnh này đó".split()
)


def tokens(s: str) -> set:
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")
    return {w for w in re.findall(r"[a-z0-9]+", s) if len(w) > 1 and w not in _STOP}


def dice(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def split_sentences(text: str) -> list:
    """Tách theo dòng gạch đầu dòng trước, rồi tới dấu kết câu."""
    out = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"(?<=[.!?])\s+", line)
        out += [p.strip() for p in parts if p.strip()]
    return out


def coverage(sentence: str, ctx_tokens: set) -> float:
    """Tỉ lệ token của *câu* có mặt trong ngữ cảnh.

    Không dùng Dice: ngữ cảnh dài 200+ token còn câu chỉ 15 token, Dice luôn nhỏ
    (~0,1) kể cả khi câu lấy nguyên văn từ ngữ cảnh. Ở đây hỏi đúng câu hỏi cần:
    "bao nhiêu phần của câu này có trong ngữ cảnh".
    """
    t = tokens(sentence)
    if not t:
        return 0.0
    return len(t & ctx_tokens) / len(t)


def support(sentence: str, ctx_tokens: set) -> float:
    return coverage(sentence, ctx_tokens)


def prune(answer: str, contexts: list, min_support: float = MIN_SUPPORT,
          min_keep: float = MIN_KEEP):
    """Trả về (câu trả lời đã lọc, tỉ lệ câu giữ lại). Tỉ lệ thấp = không có ngữ cảnh."""
    ctx = set()
    for c in contexts:
        ctx |= tokens(c)
    sents = split_sentences(answer)
    if not sents:
        return "", 0.0
    kept = [s for s in sents if support(s, ctx) >= min_support]
    ratio = len(kept) / len(sents)
    if ratio < min_keep:
        return "", ratio
    # giữ nguyên thứ tự và dấu gạch đầu dòng gốc
    text = "\n".join(
        s if s.startswith(("-", "•", "*", "1", "2", "3", "4", "5")) else f"- {s}"
        for s in kept
    )
    return text, ratio


def report(answer: str, contexts: list) -> dict:
    """Chi tiết để đo: điểm từng câu và tỉ lệ giữ lại."""
    ctx = set()
    for c in contexts:
        ctx |= tokens(c)
    sents = split_sentences(answer)
    scored = [(support(s, ctx), s) for s in sents]
    kept = [s for d, s in scored if d >= MIN_SUPPORT]
    return {"n": len(sents), "kept": len(kept),
            "ratio": len(kept) / len(sents) if sents else 0.0,
            "min": min((d for d, _ in scored), default=0.0),
            "mean": sum(d for d, _ in scored) / len(scored) if scored else 0.0}
