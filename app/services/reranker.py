"""Xếp hạng lại (rerank) từng cặp (câu hỏi, đoạn văn) bằng cross-encoder.

Vì sao cần: khoảng cách vector của embedding KHÔNG phân biệt được "tài liệu
đúng chủ đề" và "tài liệu gần nghĩa nhưng sai bệnh". Đo trên bộ eval 50 câu:

    nhóm bị chấm sai : top1 p50 = 0.0887
    nhóm chấm đúng   : top1 p50 = 0.0878

Hai phân bố chồng lên nhau nên không thể đặt ngưỡng. Cross-encoder đọc cả cặp
(câu hỏi + đoạn văn) cùng lúc nên chấm được "đoạn này có thật sự trả lời câu
hỏi này không", nhờ vậy mới có ngưỡng dùng được để quyết định:

    điểm cao  -> dùng tài liệu, được phép trích nguồn
    điểm thấp -> bỏ tài liệu, trả lời bằng kiến thức y khoa chuẩn

Model mặc định là mMARCO MiniLM (đa ngữ, có tiếng Việt, ~120MB, chạy CPU vài
chục ms cho mỗi cặp). Đổi bằng biến môi trường RERANK_MODEL.
"""

from __future__ import annotations

import os
import threading

MODEL_NAME = os.environ.get(
    "RERANK_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)
MAX_PAIR_CHARS = 1200   # cắt bớt đoạn văn dài cho nhanh, đủ để chấm chủ đề

_lock = threading.Lock()
_model = None
_error: str | None = None


def _load():
    global _model, _error
    if _model is not None or _error is not None:
        return _model
    with _lock:
        if _model is None and _error is None:
            try:
                from sentence_transformers import CrossEncoder

                _model = CrossEncoder(MODEL_NAME, max_length=512, device="cpu")
            except Exception as exc:  # thiếu mạng, thiếu model, hết RAM...
                _error = f"{type(exc).__name__}: {exc}"
    return _model


def available() -> bool:
    return _load() is not None


def last_error() -> str | None:
    return _error


def score(query: str, texts: list[str]) -> list[float]:
    """Điểm liên quan 0..1 cho từng đoạn (sigmoid của logit cross-encoder)."""
    if not texts:
        return []
    model = _load()
    if model is None:
        return []
    pairs = [(query, (t or "")[:MAX_PAIR_CHARS]) for t in texts]
    logits = model.predict(pairs, show_progress_bar=False, convert_to_numpy=True)
    # mMARCO MiniLM trả logit thô; đưa về 0..1 cho dễ đặt ngưỡng
    return [float(1.0 / (1.0 + pow(2.718281828, -float(x)))) for x in logits]


def rerank(query: str, docs: list, key: str = "text",
           top_n: int | None = None) -> list:
    """Gắn ``rerank`` (0..1) vào từng tài liệu và sắp lại giảm dần."""
    if not docs:
        return docs
    scores = score(query, [d.get(key, "") for d in docs])
    if not scores:
        return docs
    for d, s in zip(docs, scores):
        d["rerank"] = round(s, 4)
    out = sorted(docs, key=lambda d: d.get("rerank", 0.0), reverse=True)
    return out[:top_n] if top_n else out
