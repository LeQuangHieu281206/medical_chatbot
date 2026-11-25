"""Dựng danh mục tên thuốc dùng cho việc sửa lỗi gõ (`QueryNormalizer._drug_cand`).

Hai nguồn:
  1. `data/sources/duocthu/index.jsonl` — tên hoạt chất chính thức từ Dược thư
  2. tên trong KB có đuôi đặc trưng của tên thuốc (…mycin, …prazol, …sartan,
     …statin, …dipin …), xuất hiện ≥ MIN_FREQ lần

Nguồn (2) để bù các hoạt chất phổ biến nhưng không có chuyên luận trên mirror
(ví dụ `salbutamol`). Danh sách loại trừ để không nhận nhầm từ thường.

Chạy:
    .venv/bin/python scripts/build_drug_names.py
    .venv/bin/python scripts/build_drug_names.py --min-freq 3
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data/sources/duocthu/index.jsonl"
KB = ROOT / "data/processed/kb_merged.jsonl"
OUT = ROOT / "data/processed/drug_names.json"

WORD_RE = re.compile(r"\w+", re.U)
# Đuôi thường chỉ có ở tên thuốc
SUFFIX_RE = re.compile(
    r"(mycin|micin|cillin|cyclin|prazol|azol|olol|sartan|statin|dipin|azepam|zolam"
    r"|formin|gliptin|flozin|tidine|tidin|profen|caine|dronat|setron|triptan"
    r"|parin|xaban|grel|semid|thiazid|butamol|phyllin|terol|etamol)$"
)
# Từ thường có đuôi giống tên thuốc
STOP = {
    "cholesterol", "prolactin", "pepsin", "insulin",  # insulin vẫn là thuốc: xử lý riêng bên dưới
    "penicillin", "tetracyclin",  # vẫn là thuốc, nhưng viết dạng nhóm: giữ ở dạng số ít
}


def main():
    ap = argparse.ArgumentParser(description="Dựng danh mục tên thuốc")
    ap.add_argument("--min-freq", type=int, default=5)
    args = ap.parse_args()

    names, origin = {}, {}

    if INDEX.exists():
        for line in INDEX.open(encoding="utf-8"):
            if not line.strip():
                continue
            n = json.loads(line).get("name", "").strip()
            if n:
                names[n.lower()] = 0
                origin[n.lower()] = "duocthu"

    counts = Counter()
    kb_path = KB if KB.exists() else ROOT / "data/processed/kb.jsonl"
    for line in kb_path.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        for w in WORD_RE.findall(f"{r.get('question', '')} {r.get('answer', '')}".lower()):
            if w.isalpha() and len(w) >= 6 and SUFFIX_RE.search(w):
                counts[w] += 1

    added = 0
    for w, n in counts.items():
        if n < args.min_freq or w in names or w in STOP:
            continue
        names[w] = n
        origin[w] = "kb"
        added += 1

    # Tên thuốc luôn được coi là "đủ phổ biến" dù xuất hiện ít
    payload = {
        "names": sorted(names),
        "freq": names,
        "origin": origin,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")

    print(f"Đã ghi {OUT.relative_to(ROOT)}: {len(names)} tên "
          f"({len(names) - added} từ Dược thư, {added} bổ sung từ KB)")
    print("  mẫu bổ sung:", [w for w, o in origin.items() if o == "kb"][:12])


if __name__ == "__main__":
    main()
