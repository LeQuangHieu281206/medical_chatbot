import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ner import extract_entities

CASES = [
    "Tôi bị đau đầu và sốt cao ba ngày nay, có nên uống paracetamol không?",
    "Mổ nội soi cắt túi mật có nguy hiểm không?",
    "Bé 2 tuổi bị ho, sổ mũi, nên dùng thuốc gì?",
    "Tiểu đường uống metformin có tác dụng phụ gì?",
    "Khi nào cần đi khám khi bị cúm?",
    "Công thức nấu phở bò",
]

for i, q in enumerate(CASES):
    t0 = time.perf_counter()
    ents = extract_entities(q)
    ms = (time.perf_counter() - t0) * 1000
    print(f"\n[{ms:7.0f} ms] {q}")
    for e in ents:
        print(f"    {e['label']:20s} {e['text']}")
    if not ents:
        print("    (không có thực thể)")
    if i == 0:
        print("    ^ lần gọi đầu gồm cả thời gian nạp mô hình")