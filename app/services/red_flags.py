"""Nhận diện dấu hiệu cấp cứu trong câu hỏi (red flag) từ một tệp dữ liệu.

Trước đây danh sách này là một regex hard-code trong `pipeline.py`. Nay nội
dung nằm ở `data/sources/red_flags.jsonl` để thêm/sửa không phải sửa code, và
mỗi nhóm có lời khuyên sơ cứu riêng thay vì một câu chung.

Mỗi dòng dữ liệu:
    id, nhom, uu_tien, mau (danh sách mẫu, so khớp trên câu đã chuẩn hoá),
    loi_khuyen (danh sách dòng, KHÔNG chứa liều thuốc cụ thể)
    khong_khop (tuỳ chọn): nếu câu khớp một mẫu này thì huỷ kết quả
    kem_theo   (tuỳ chọn): câu phải khớp thêm một mẫu này mới tính

`khong_khop` để chặn báo nhầm ("ngừng thở khi ngủ" không phải ngừng tim,
"ngộ độc thực phẩm" không phải ngộ độc cấp). `kem_theo` buộc đủ ngữ cảnh:
"chảy máu cam" chỉ tính khi câu có nhắc sốt.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/sources/red_flags.jsonl"

# Câu chung, luôn đứng đầu khối cảnh báo
EMERGENCY = (
    "Nếu đây là tình huống khẩn cấp đang xảy ra, hãy gọi 115 hoặc đưa người bệnh "
    "đến cơ sở y tế gần nhất ngay, không chờ câu trả lời của chatbot."
)


@dataclass(frozen=True)
class Flag:
    id: str
    nhom: str
    uu_tien: int
    pattern: re.Pattern
    loi_khuyen: tuple[str, ...]
    veto: re.Pattern | None = None      # khớp thì huỷ
    must: re.Pattern | None = None      # phải khớp thêm


@lru_cache(maxsize=1)
def load_flags() -> tuple[Flag, ...]:
    """Nạp và biên dịch một lần; trả về theo thứ tự ưu tiên tăng dần."""
    if not DATA.exists():
        return ()
    flags = []
    for line in DATA.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        # "..." = "cách nhau vài từ" (mang thai ... ra máu). Đây là quy ước của
        # riêng tệp này, không phải regex đầy đủ, để người soát nội dung viết được
        # câu có khoảng cách mà không phải biết regex.
        gap = lambda s: s.replace("...", ".{0,25}?")   # tác giả đã có dấu cách hai bên
        pats = [gap(p.strip()) for p in r.get("mau", []) if p.strip()]
        if not pats:
            continue
        veto = [gap(p.strip()) for p in r.get("khong_khop", []) if p.strip()]
        must = [gap(p.strip()) for p in r.get("kem_theo", []) if p.strip()]
        flags.append(Flag(
            id=r["id"],
            nhom=r["nhom"],
            uu_tien=int(r.get("uu_tien", 99)),
            pattern=re.compile("|".join(pats), re.IGNORECASE),
            loi_khuyen=tuple(r.get("loi_khuyen", [])),
            veto=re.compile("|".join(veto), re.IGNORECASE) if veto else None,
            must=re.compile("|".join(must), re.IGNORECASE) if must else None,
        ))
    flags.sort(key=lambda f: f.uu_tien)
    return tuple(flags)


def _fires(flag: Flag, text: str) -> bool:
    if flag.must is not None and not flag.must.search(text):
        return False
    if flag.veto is not None and flag.veto.search(text):
        return False
    return bool(flag.pattern.search(text))


def match(text: str) -> Flag | None:
    """Nhóm cấp cứu khớp đầu tiên (ưu tiên cao nhất) hoặc None."""
    if not text:
        return None
    for f in load_flags():
        if _fires(f, text):
            return f
    return None


def matches(text: str) -> list[Flag]:
    """Mọi nhóm khớp, theo thứ tự ưu tiên (để kiểm thử / hiện nhiều nhóm)."""
    return [f for f in load_flags() if text and _fires(f, text)]


def prefix(text: str, generic: bool = True) -> str:
    """Khối cảnh báo đặt lên đầu câu trả lời; chuỗi rỗng nếu không có red flag.

    Câu gọi cấp cứu chung đứng trước để hành động khẩn cấp luôn là dòng đầu
    tiên người dùng đọc (và để các test cũ kiểm `text.startswith(EMERGENCY)`
    vẫn đúng).
    """
    flag = match(text)
    if flag is None:
        return ""
    lines = []
    if generic:
        lines += [EMERGENCY, ""]
    lines.append(f"⚠️ {flag.nhom.upper()} — hướng dẫn sơ cứu ban đầu:")
    lines += list(flag.loi_khuyen)
    return "\n".join(lines)


def union_pattern() -> re.Pattern:  # noqa: D401 - giữ cho tương thích pipeline cũ
    """Một regex gộp mọi nhóm, dùng cho chỗ chỉ cần biết có/không."""
    parts = [f.pattern.pattern for f in load_flags()]
    return re.compile("|".join(f"(?:{p})" for p in parts), re.IGNORECASE) if parts else re.compile(r"(?!x)x")
