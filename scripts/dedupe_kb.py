"""Gộp câu hỏi trùng trong kb.jsonl / eval.jsonl, giữ bản có nguồn và đáp án dài nhất.

Mặc định chỉ in kế hoạch. Ghi thật khi có `--apply` (có backup trước khi ghi).

Hai chế độ:
  - mặc định: trùng **khít** (cùng câu sau khi chuẩn hoá NFC + chữ thường + bỏ dấu câu)
  - `--near`: thêm cả gần trùng (Jaccard >= 0.70). Cần người duyệt danh sách loại
    trước, vì câu hỏi khác nhau một chút có thể là hai ý khác nhau.

Sau khi sửa kb.jsonl phải chạy lại chunk + nạp lại ChromaDB, vì `parent_id` trong
kb_chunked.jsonl trỏ theo chỉ số dòng:

    .venv/bin/python scripts/dedupe_kb.py data/processed/kb.jsonl --apply
    .venv/bin/python scripts/rechunk_qa.py
    .venv/bin/python app/services/ingest_kb.py

Chạy:
    .venv/bin/python scripts/dedupe_kb.py data/processed/kb.jsonl            # xem kế hoạch
    .venv/bin/python scripts/dedupe_kb.py data/processed/kb.jsonl --apply    # ghi thật
"""
import argparse
import csv
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.data_quality import find_duplicates, norm, pick_keeper  # noqa: E402

AUDIT = ROOT / "data/audit"
BACKUP = AUDIT / "backup"
DROP_CSV = AUDIT / "dropped_duplicates.csv"
DROP_COLUMNS = ["file", "group", "keep_id", "drop_id", "link_keep", "answer_len_keep",
                "answer_len_drop", "question"]


def load(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def plan(rows: list, near: bool) -> list:
    """Trả về [(keep_id, [drop_id, ...], lý do)] cho từng nhóm trùng."""
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[norm(r.get("question") or "")].append(i)
    exact = [ids for key, ids in groups.items() if key and len(ids) > 1]

    if near:
        near_groups, _ = find_duplicates(rows)
        covered = {i for ids in exact for i in ids}
        extra = [ids for ids in near_groups.values() if not covered & set(ids)]
    else:
        extra = []

    out = []
    for ids in exact + extra:
        if len(ids) < 2:
            continue
        keep = pick_keeper(rows, ids)
        out.append((keep, [i for i in ids if i != keep],
                    "trùng khít" if ids in exact else "gần trùng"))
    return out


def show(rows, drops, path: Path):
    print(f"\n== {path.relative_to(ROOT)} ({len(rows)} dòng) ==")
    if not drops:
        print("  không có câu trùng — không cần sửa")
        return
    for gid, (keep, drop_ids, why) in enumerate(drops, 1):
        k = rows[keep]
        print(f"\n  [{gid}] {why}: giữ dòng {keep} "
              f"({len(k['answer'])} ký tự, {'có' if k['link'] else 'KHÔNG'} nguồn)")
        print(f"      {k['question'][:100]}")
        for i in drop_ids:
            d = rows[i]
            print(f"      - xoá dòng {i} ({len(d['answer'])} ký tự, "
                  f"{'có' if d['link'] else 'KHÔNG'} nguồn): {d['question'][:80]}")
            if d["answer"].strip() != k["answer"].strip():
                print(f"        đáp án khác 60 ký tự đầu: {d['answer'][:60]!r}")


def write_drops(path: Path, drops, rows):
    AUDIT.mkdir(parents=True, exist_ok=True)
    new = not DROP_CSV.exists()
    with DROP_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(DROP_COLUMNS)
        for gid, (keep, drop_ids, _why) in enumerate(drops, 1):
            for i in drop_ids:
                w.writerow([path.name, gid, keep, i, int(bool(rows[keep]["link"])),
                            len(rows[keep]["answer"]), len(rows[i]["answer"]),
                            rows[i]["question"][:200]])


def apply(path: Path, rows, drops) -> int:
    drop_ids = {i for _, ids, _ in drops for i in ids}
    keep_rows = [r for i, r in enumerate(rows) if i not in drop_ids]

    BACKUP.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUP / f"{path.name}.{stamp}.bak"
    shutil.copy2(path, backup)

    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep_rows),
                    encoding="utf-8")
    print(f"\n  ghi {path.relative_to(ROOT)}: {len(rows)} -> {len(keep_rows)} dòng "
          f"(xoá {len(drop_ids)})")
    print(f"  backup: {backup.relative_to(ROOT)}")
    return len(keep_rows)


def main():
    ap = argparse.ArgumentParser(description="Gộp câu hỏi trùng trong KB")
    ap.add_argument("files", nargs="+", help="file .jsonl cần gộp trùng")
    ap.add_argument("--near", action="store_true", help="gộp cả câu gần trùng (Jaccard >= 0.70)")
    ap.add_argument("--apply", action="store_true", help="ghi thật (mặc định chỉ xem kế hoạch)")
    args = ap.parse_args()

    for name in args.files:
        path = (ROOT / name) if not Path(name).is_absolute() else Path(name)
        rows = load(path)
        drops = plan(rows, args.near)
        show(rows, drops, path)
        if not drops:
            continue
        if args.apply:
            write_drops(path, drops, rows)
            apply(path, rows, drops)

    print("\nBảng dòng đã xoá (để truy vết): data/audit/dropped_duplicates.csv")
    if not args.apply:
        print("Chưa ghi gì — thêm --apply để sửa thật.")
        return 0
    print("Nếu vừa sửa kb.jsonl: chạy lại `scripts/rechunk_qa.py` rồi "
          "`app/services/ingest_kb.py` để ChromaDB khớp dữ liệu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
