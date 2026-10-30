# tests/21_test_seizure_note.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pipeline import SEIZURE_NOTE, sanitize_answer

CASES = [
    # (câu hỏi, câu trả lời của qwen, kỳ vọng có SEIZURE_NOTE)
    ("Suy thận cấp biểu hiện thế nào?", "- Có thể gặp co giật hoặc hôn mê.", False),
    ("Bé bị co giật phải làm gì?", "- Đặt bé nằm nghiêng.", True),
    ("Bé bị co giật phải làm gì?",
     "- Không đưa vật gì vào miệng bé.", False),  # đã có sẵn, không lặp
    ("Động kinh sơ cứu thế nào?", "- Giữ môi trường an toàn.", True),
]

bad = 0
for q, ans, expect in CASES:
    out = sanitize_answer(ans, q)
    got = SEIZURE_NOTE in out
    ok = got == expect
    bad += not ok
    print(("OK  " if ok else "SAI ") + f"{q} -> có ghi chú: {got} (kỳ vọng {expect})")
print(f"\nSai: {bad}/{len(CASES)}")