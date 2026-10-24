import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb
from app.services.topic_filter import COLLECTION, DB_PATH

col = chromadb.PersistentClient(path=DB_PATH).get_collection(COLLECTION)
print("Tổng số document:", col.count())

KEYWORDS = [
    "cúm", "cảm cúm", "tiểu đường", "huyết áp", "sốt xuất huyết", "dạ dày",
    "hen", "viêm gan", "Covid", "tiêu chảy", "đau đầu", "dị ứng", "gout",
    "thiếu máu", "trầm cảm", "mang thai", "vaccine", "ung thư",
]

print(f"\n{'từ khoá':18s} {'số document':>12s}")
for kw in KEYWORDS:
    ids = set()
    for variant in {kw, kw.capitalize(), kw.lower()}:
        res = col.get(where_document={"$contains": variant}, include=[])
        ids.update(res["ids"])
    print(f"{kw:18s} {len(ids):12d}")

print("\n== 3 document đầu tiên chứa 'cúm' ==")
res = col.get(where_document={"$contains": "cúm"}, limit=3, include=["documents"])
for d in res["documents"]:
    print("-", d[:250].replace("\n", " | "))