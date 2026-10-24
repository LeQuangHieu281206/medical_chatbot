import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.pipeline import MedicalChatbot

CASES = [
    "Khi nào cần đi khám khi bị cúm?",
    "Trẻ bị sốt cao co giật thì xử lý thế nào?",
    "Uống paracetamol mỗi ngày bao nhiêu mg là đủ?",
    "Công thức nấu phở bò",
]

bot = MedicalChatbot()

for q in CASES:
    a = bot.ask(q)
    print("\n" + "=" * 70)
    print("Hỏi:", q)
    print(f"Lọc chủ đề: {a.topic.zone} (d={a.topic.distance:.3f}) - {a.topic.reason}")
    if a.entities:
        print("Thực thể:", "; ".join(f"{e['text']} [{e['label']}]" for e in a.entities))
    for s in a.sources:
        print(f"  nguồn d={s['distance']:.3f} | {s['question'][:70]}")
    print("\nTrả lời:\n" + a.text)
    print("\nThời gian (ms):", a.timings)