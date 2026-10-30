# tests/24_show_context.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ner import extract_entities
from app.services.pipeline import MedicalChatbot


def main():
    q = " ".join(sys.argv[1:]) or "Thuốc Atorlog có thể tương tác với thuốc nào?"
    bot = MedicalChatbot()
    docs = bot.retrieve(q, extract_entities(q), True)
    print(f"Câu hỏi: {q}\n")
    for i, d in enumerate(docs, 1):
        print(f"[{i}] d={d['distance']:.3f} dài {len(d['text'])} ký tự | {d['question']}")
        print(d["text"])
        print()


if __name__ == "__main__":
    main()