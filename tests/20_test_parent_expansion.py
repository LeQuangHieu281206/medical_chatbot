# tests/20_test_parent_expansion.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time

from app.services.ner import extract_entities
from app.services.pipeline import MedicalChatbot, sanitize_answer

QUESTIONS = [
    "Khi nào cần đi khám khi bị cúm?",
    "Suy thận cấp có thể biểu hiện ra ngoài như thế nào?",
    "Thuốc Atorlog có thể tương tác với thuốc nào?",
    "Tỳ bà diệp thường được dùng để chữa bệnh gì?",
    "Bệnh tiểu đường type 2 có triệu chứng gì?",
    "Paracetamol là thuốc gì?",
]
GEN_N = 2  # số câu đầu chạy qwen khi có --gen


def show(tag, docs, ms):
    total = sum(len(d["text"]) for d in docs)
    print(f"  [{tag}] {len(docs)} đoạn, {total} ký tự, truy xuất {ms} ms")
    for d in docs:
        print(f"     d={d['distance']:.3f} [{d['source'] or '-'}] {d['question'][:75]}")


def main():
    gen = "--gen" in sys.argv
    bot = MedicalChatbot()
    bot.warmup()
    for idx, q in enumerate(QUESTIONS):
        print("=" * 100)
        print(f"Hỏi: {q}")
        ents = extract_entities(q)
        print("  Thực thể:", ", ".join(e["text"] for e in ents) or "không có")

        results = {}
        for tag, expand in (("cũ ", False), ("mới", True)):
            t0 = time.perf_counter()
            docs = bot.retrieve(q, ents, True, expand=expand)
            ms = round((time.perf_counter() - t0) * 1000)
            results[tag] = docs
            show(tag, docs, ms)

        if gen and idx < GEN_N:
            for tag, docs in results.items():
                text, stats = bot.generate(q, ents, docs)
                print(f"\n  --- Câu trả lời [{tag}] ---")
                print(f"  prompt {stats.get('prompt_tokens')} token / {stats.get('prompt_s')}s, "
                      f"sinh {stats.get('gen_tokens')} token / {stats.get('gen_s')}s")
                print("  " + sanitize_answer(text, q).replace("\n", "\n  "))


if __name__ == "__main__":
    main()