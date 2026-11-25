"""Audit dữ liệu KB: câu hỏi gần trùng, dòng thiếu nguồn, đáp án quá dài, phủ chuyên khoa.

Chỉ ĐỌC data/processed/kb.jsonl và GHI báo cáo vào data/audit/. Không sửa dữ liệu gốc.

Chạy: .venv/bin/python tests/40_data_audit.py
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.data_quality import (  # noqa: E402
    JACCARD_MIN,
    find_duplicates,
    pick_keeper,
)
from app.services.topic_taxonomy import tag_topic  # noqa: E402

KB = ROOT / "data/processed/kb.jsonl"
OUT = ROOT / "data/audit"

LONG_ANSWER = 800       # ký tự


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in KB.open(encoding="utf-8") if l.strip()]
    print(f"KB: {len(rows)} dòng | nguồn: {dict(Counter(r['source'] for r in rows))}")

    # --- 1. câu hỏi gần trùng ---
    dup_groups, _ = find_duplicates(rows)
    extra = sum(len(v) - 1 for v in dup_groups.values())
    print(f"\n[1] Nhóm gần trùng (Jaccard >= {JACCARD_MIN}): {len(dup_groups)} "
          f"| số dòng dư: {extra}")

    with (OUT / "duplicates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group", "role", "id", "question", "answer_len", "has_link", "source"])
        for gid, (root_id, ids) in enumerate(sorted(dup_groups.items(), key=lambda kv: -len(kv[1])), 1):
            keep = pick_keeper(rows, ids)
            for i in ids:
                r = rows[i]
                w.writerow([gid, "keep" if i == keep else "dup", i,
                            r["question"][:200], len(r["answer"]),
                            int(bool(r["link"])), r["source"]])
    for root_id, ids in sorted(dup_groups.items(), key=lambda kv: -len(kv[1]))[:3]:
        print(f"    nhóm {len(ids)} dòng:")
        for i in ids[:4]:
            print(f"      - [{rows[i]['source']}] {rows[i]['question'][:85]}")

    # --- 2. thiếu nguồn ---
    no_link = [(i, r) for i, r in enumerate(rows) if not r["link"]]
    print(f"\n[2] Dòng thiếu link nguồn: {len(no_link)} ({100 * len(no_link) // len(rows)}%)")
    with (OUT / "missing_link.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "source", "question"])
        for i, r in no_link:
            w.writerow([i, r["source"], r["question"][:200]])

    # --- 3. đáp án quá dài / vượt 512 token ---
    long_ = [r for r in rows if len(r["answer"]) > LONG_ANSWER]
    over_512 = [r for r in rows if len(r["answer"]) > 1600]   # ~4 ký tự/token
    print(f"\n[3] Đáp án > {LONG_ANSWER} ký tự: {len(long_)} ({100 * len(long_) // len(rows)}%) "
          f"| ước vượt 512 token của e5: {len(over_512)}")
    print(f"    khi đưa vào prompt chỉ còn {350} ký tự -> mất "
          f"{sum(1 for r in long_ if len(r['answer']) > 1000)} dòng bị cắt phần lớn nội dung")

    # --- 4. phủ chuyên khoa ---
    tags = [tag_topic(r["question"], r["answer"]) for r in rows]
    dist = Counter(tags)
    print(f"\n[4] Phủ chuyên khoa ({len(dist)} nhóm):")
    for name, n in dist.most_common():
        print(f"    {name:<16}{n:>6}  {100 * n / len(rows):>5.1f}%")
    with (OUT / "kb_topics.jsonl").open("w", encoding="utf-8") as f:
        for r, t in zip(rows, tags):
            f.write(json.dumps({"topic": t, "source": r["source"],
                                "question": r["question"]}, ensure_ascii=False) + "\n")

    print(f"\nĐã ghi: {OUT}/duplicates.csv, missing_link.csv, kb_topics.jsonl")
    print("Chưa sửa gì trong kb.jsonl — duyệt CSV rồi mới quyết định xoá/gộp.")


if __name__ == "__main__":
    main()
