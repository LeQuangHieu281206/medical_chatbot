"""Mở rộng truy vấn: từ triệu chứng suy ra tên bệnh trước khi truy xuất.

Vì sao cần: đo bằng ``tests/56_doc_recall.py`` — câu hỏi kiểu "bố tôi 55 tuổi
khát nước liên tục, tiểu đêm, sụt 4kg" không truy xuất được bài nào có tiêu đề
"Đái tháo đường", dù kho có 377 bài như vậy. Nguyên nhân: câu hỏi chỉ mô tả
triệu chứng, không chứa tên bệnh, nên embedding và BM25 đều bám vào các bài
nói về triệu chứng tiết niệu.

Cách làm: hỏi chính model local sinh 2-3 tên bệnh khả dĩ, rồi nối vào truy vấn
truy xuất (cả dense lẫn BM25 đều dùng chuỗi này). Kết quả được cache theo câu
hỏi để không gọi lại model.

Bật bằng biến môi trường ``QUERY_EXPAND=1``. Tắt mặc định vì mỗi câu tốn thêm
một lượt gọi model; chỉ bật khi đo thấy recall tăng.
"""

from __future__ import annotations

import re

CACHE: dict[str, list[str]] = {}
MAX_TERMS = 3

PROMPT = (
    "Bạn là bác sĩ đa khoa. Từ câu hỏi của người bệnh dưới đây, liệt kê tối đa 3 tên "
    "bệnh hoặc tình trạng y khoa có khả năng nhất, mỗi dòng một tên, viết bằng tiếng "
    "Việt, không giải thích, không đánh số, không thêm chữ nào khác."
)

BAD = re.compile(
    r"^(?:[-*•\d.)\s]|bệnh nhân|câu hỏi|trả lời|dưới đây|tên bệnh)", re.I
)


def _clean(text: str) -> list[str]:
    out = []
    for line in (text or "").splitlines():
        line = line.strip().strip("*#` ")
        line = re.sub(r"^[\-\*\u2022\d.)]+\s*", "", line)
        line = line.split("(")[0].strip(" .:;,-")
        if not line or len(line) > 60 or BAD.match(line):
            continue
        if line.lower() in {x.lower() for x in out}:
            continue
        out.append(line)
        if len(out) >= MAX_TERMS:
            break
    return out


def expand(question: str, provider: str | None = None,
           model: str | None = None) -> list[str]:
    """Trả về danh sách tên bệnh khả dĩ (rỗng nếu lỗi — không chặn câu trả lời)."""
    key = (question or "").strip().lower()
    if not key:
        return []
    if key in CACHE:
        return CACHE[key]
    try:
        from app.services import llm

        text = llm.chat(
            [{"role": "system", "content": PROMPT},
             {"role": "user", "content": question}],
            temperature=0.1, max_tokens=80, provider=provider, model=model,
        )
        terms = _clean(text)
    except Exception:
        terms = []
    CACHE[key] = terms
    return terms


def augment(question: str, terms: list[str]) -> str:
    """Nối tên bệnh vào câu hỏi để truy xuất bám được vào tiêu đề bài viết."""
    if not terms:
        return question
    return question + " " + " ".join(terms)
