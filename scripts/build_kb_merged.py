"""Gộp QA thường (kb.jsonl) với QA thuốc (kb_drugs_*.jsonl) thành một KB duy nhất.

Pipeline chỉ đọc một collection QA (`medical_kb`), nên mọi thứ cần truy hồi phải
nằm trong cùng một file trước khi nạp.

Chạy:
    .venv/bin/python scripts/build_kb_merged.py
    .venv/bin/python scripts/build_kb_merged.py --extra data/processed/kb_drugs_25_full.jsonl

Kết quả: data/processed/kb_merged.jsonl (giữ nguyên thứ tự kb.jsonl trước, nối thuốc sau)
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.data_quality import norm  # noqa: E402

DEFAULT_BASE = "data/processed/kb.jsonl"
DEFAULT_EXTRA = "data/processed/kb_drugs_full.jsonl"
DEFAULT_OUT = "data/processed/kb_merged.jsonl"


def load(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser(description="Gộp KB thường + KB thuốc")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--extra", action="append", default=None,
                    help="file cần nối thêm (lặp lại được; mặc định kb_drugs_full.jsonl)")
    ap.add_argument("--exclude", action="append", default=None,
                    help="file có câu hỏi KHÔNG được xuất hiện trong KB (vd tập eval held-out)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    base = load(ROOT / args.base)
    extras = [ROOT / p for p in (args.extra or [DEFAULT_EXTRA])]
    print(f"Gốc: {args.base} — {len(base)} dòng")
    for p in extras:
        print(f"Nối: {p.relative_to(ROOT)} — {len(load(p))} dòng")

    seen = {norm(r["question"]) for r in base}
    # câu hỏi held-out không được lọt vào KB, kể cả từ file mới
    blocked = set()
    for p in (args.exclude or []):
        blocked |= {norm(r["question"]) for r in load(ROOT / p)}
    if blocked:
        print(f"Chặn {len(blocked)} câu hỏi held-out từ: {', '.join(args.exclude)}")
    out, skipped = list(base), Counter()
    for p in extras:
        for r in load(p):
            key = norm(r["question"])
            if key in blocked:
                skipped[p.name + " (held-out)"] += 1
                continue
            if key in seen:
                skipped[p.name] += 1
                continue
            seen.add(key)
            out.append(r)

    out_path = ROOT / args.out
    out_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
                        encoding="utf-8")
    print(f"\nĐã ghi {out_path.relative_to(ROOT)}: {len(out)} dòng")
    for name, n in skipped.items():
        print(f"  bỏ {n} dòng trùng câu hỏi trong {name}")
    print("  theo nguồn:", dict(Counter(r["source"] for r in out)))
    if skipped:
        print("  Lưu ý: dòng trùng bị bỏ, không sửa nội dung gốc.")
    print("\nBước tiếp: .venv/bin/python scripts/rechunk_qa.py "
          f"--kb {args.out} --out {args.out.replace('.jsonl', '_chunked.jsonl')}")


if __name__ == "__main__":
    main()
