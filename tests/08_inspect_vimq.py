import json
from pathlib import Path
from collections import Counter

root = Path("data/raw/ViMQ")

print("== Cây thư mục ==")
for p in sorted(root.rglob("*")):
    if p.is_file() and ".git" not in p.parts:
        print(p.relative_to(root), f"{p.stat().st_size/1024:.0f} KB")

print("\n== Đọc thử các file dữ liệu ==")
for p in sorted(root.rglob("*")):
    if p.suffix in {".json", ".jsonl", ".txt", ".conll", ".csv"} and ".git" not in p.parts:
        print(f"\n--- {p.relative_to(root)} ---")
        with open(p, encoding="utf-8") as f:
            head = [next(f, "") for _ in range(8)]
        print("".join(head)[:1200])