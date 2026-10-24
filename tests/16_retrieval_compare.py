import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ner import extract_entities
from app.services.pipeline import MedicalChatbot

QUESTIONS = [
    "Khi nào cần đi khám khi bị cúm?",
    "Bệnh cúm là gì?",
    "Tiểu đường type 2 có nguy hiểm không?",
    "Sốt xuất huyết có những dấu hiệu nào?",
    "Paracetamol là thuốc gì?",
    "Đau đầu kéo dài có nguy hiểm không?",
]

bot = MedicalChatbot()
print("Collection bách khoa:", "có" if bot.encyc is not None else "KHÔNG CÓ")

for q in QUESTIONS:
    ents = extract_entities(q)
    docs = bot.retrieve(q, ents)
    print("\nHỏi:", q)
    print("  Thực thể:", "; ".join(e["text"] for e in ents) or "-")
    for d in docs:
        print(f"  d={d['distance']:.3f} | {d['source'] or '?':9s} | {d['question'][:80]}")