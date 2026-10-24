import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.pipeline import MedicalChatbot

CASES = [
    "Uống paracetamol mỗi ngày bao nhiêu mg là đủ?",
    "Bé 10 kg bị sốt thì cho uống hạ sốt liều bao nhiêu?",
    "Mỗi ngày nên uống bao nhiêu nước?",
    "Bị đau ngực khó thở thì nên làm gì?",
    "Trẻ bị sốt cao co giật thì xử lý thế nào?",
]

bot = MedicalChatbot()
t0 = time.perf_counter()
bot.warmup()
print(f"Khởi động (nạp sẵn NER + qwen): {time.perf_counter() - t0:.1f} s")

for q in CASES:
    t0 = time.perf_counter()
    a = bot.ask(q)
    total = time.perf_counter() - t0
    print("\n" + "=" * 70)
    print("Hỏi:", q)
    print(f"Lọc chủ đề: {a.topic.zone} | Thực thể:",
          "; ".join(f"{e['text']} [{e['label']}]" for e in a.entities) or "-")
    print("\nTrả lời:\n" + a.text)
    print(f"\nTổng {total:.1f} s | chi tiết: {a.timings}")