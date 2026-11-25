"""Nhận kết quả soát red flag từ AI (Claude/ChatGPT) và đối chiếu với bản đang dùng.

AI thường trả về cả một bài văn, phần file nằm trong khối ```json ...``` hoặc
``` ... ```. Script tìm các dòng JSON hợp lệ, kiểm bằng `validate_data.py`, in
khác biệt so với bản hiện tại, rồi ghi ra file ứng viên. Không đè file đang dùng
trừ khi có `--apply`.

Chạy:
    .venv/bin/python scripts/merge_red_flags.py answer.md
    .venv/bin/python scripts/merge_red_flags.py answer.md --apply
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data/sources/red_flags.jsonl"
CANDIDATE = ROOT / "data/audit/red_flags_candidate.jsonl"
BACKUP_DIR = ROOT / "data/audit/backup"
FIELDS = ("id", "nhom", "uu_tien", "mau", "loi_khuyen")
DOSE = re.compile(r"\d+\s*(mg|mcg|µg|μg|ml|gói|ống|viên)\b", re.IGNORECASE)


def extract(path: Path) -> list:
    """Lấy các object JSON có đủ trường red flag từ một file văn bản bất kỳ."""
    rows, seen = [], set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip().rstrip(",")
        if not s.startswith("{"):
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or not all(f in obj for f in FIELDS):
            continue
        if obj["id"] in seen:
            continue
        seen.add(obj["id"])
        rows.append(obj)
    return rows


def norm_lines(v):
    """So sánh lời khuyên bỏ qua khác biệt khoảng trắng và gạch đầu dòng."""
    if isinstance(v, str):
        v = [v]
    return [re.sub(r"^\W+", "", str(x)).strip() for x in (v or [])]


def diff(old: list, new: list) -> None:
    o = {r["id"]: r for r in old}
    n = {r["id"]: r for r in new}
    added = [i for i in n if i not in o]
    removed = [i for i in o if i not in n]
    print(f"\nNhóm: giữ {len(set(o) & set(n))}, thêm {len(added)}, bỏ {len(removed)}")
    if added:
        print("  thêm:", ", ".join(f"{i} ({n[i].get('nhom', '')})" for i in added))
    if removed:
        print("  bỏ  :", ", ".join(f"{i} ({o[i].get('nhom', '')})" for i in removed))

    for i in [k for k in n if k in o]:
        a, b = o[i], n[i]
        changes = []
        if a.get("nhom") != b.get("nhom"):
            changes.append(f"nhom: {a.get('nhom')!r} -> {b.get('nhom')!r}")
        if a.get("uu_tien") != b.get("uu_tien"):
            changes.append(f"uu_tien: {a.get('uu_tien')} -> {b.get('uu_tien')}")
        ma, mb = set(a.get("mau") or []), set(b.get("mau") or [])
        if ma - mb:
            changes.append("mẫu bỏ: " + "; ".join(sorted(ma - mb)))
        if mb - ma:
            changes.append("mẫu thêm: " + "; ".join(sorted(mb - ma)))
        la, lb = norm_lines(a.get("loi_khuyen")), norm_lines(b.get("loi_khuyen"))
        if la != lb:
            changes.append(f"lời khuyên: {len(la)} -> {len(lb)} dòng")
            for line in lb:
                if line not in la:
                    changes.append(f"   + {line[:100]}")
            for line in la:
                if line not in lb:
                    changes.append(f"   - {line[:100]}")
        if changes:
            print(f"\n[{i}]")
            for c in changes:
                print(f"  {c}")


def check_dose(rows: list) -> list:
    return [(r["id"], l) for r in rows for l in (r.get("loi_khuyen") or []) if DOSE.search(str(l))]


def run_validator(path: Path) -> bool:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_data.py"), str(path), "--strict"],
        capture_output=True, text=True,
    )
    tail = [l for l in r.stdout.splitlines() if l.startswith(("  [FAIL]", "ĐẠT", "KHÔNG ĐẠT"))]
    print("\n".join(tail) if tail else r.stdout[-500:])
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description="Đối chiếu bản red flag do AI soát")
    ap.add_argument("answer", help="file chứa câu trả lời của AI (.md/.txt)")
    ap.add_argument("--apply", action="store_true", help="ghi đè data/sources/red_flags.jsonl")
    args = ap.parse_args()

    src = Path(args.answer)
    if not src.exists():
        print(f"Không thấy file {src}")
        return 1
    rows = extract(src)
    if not rows:
        print("Không tìm được dòng JSON nào có đủ trường id/nhom/uu_tien/mau/loi_khuyen.")
        print("Kiểm lại: AI có xuất PHẦN 3 (file JSONL) không, mỗi object một dòng.")
        return 1

    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATE.open("w", encoding="utf-8") as f:
        for r in sorted(rows, key=lambda x: x.get("uu_tien", 99)):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Đã tách {len(rows)} nhóm từ {src.name} → {CANDIDATE.relative_to(ROOT)}")

    old = [json.loads(l) for l in CURRENT.open(encoding="utf-8") if l.strip()]
    diff(old, rows)

    bad = check_dose(rows)
    if bad:
        print(f"\nCẢNH BÁO: {len(bad)} dòng lời khuyên có liều thuốc bằng số:")
        for i, l in bad:
            print(f"  [{i}] {l[:100]}")

    print("\n== validate_data.py --strict trên bản ứng viên ==")
    ok = run_validator(CANDIDATE)

    if not args.apply:
        print("\nChưa ghi đè. Đọc khác biệt ở trên rồi chạy lại với --apply.")
        return 0 if ok and not bad else 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / "red_flags.jsonl"
    shutil.copy2(CURRENT, backup)
    shutil.copy2(CANDIDATE, CURRENT)
    print(f"\nĐã ghi đè {CURRENT.relative_to(ROOT)} (bản cũ: {backup.relative_to(ROOT)})")
    print("Chạy tiếp: .venv/bin/python tests/54_test_red_flags.py -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
