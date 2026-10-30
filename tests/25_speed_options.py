# tests/25_speed_options.py
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ollama

from app.services.ner import extract_entities
from app.services.pipeline import KEEP_ALIVE, SYSTEM_PROMPT, MedicalChatbot
from app.services.topic_filter import LLM_MODEL

QUESTION = "Khi nào cần đi khám khi bị cúm?"
NUM_PREDICT = 60
REPEATS = 2
CONFIGS = [
    {"num_ctx": 4096},
    {"num_ctx": 2560},
    {"num_ctx": 2560, "num_thread": 4},
    {"num_ctx": 2560, "num_thread": 6},
    {"num_ctx": 2560, "num_thread": 8},
]


def build_user(bot):
    ents = extract_entities(QUESTION)
    docs = bot.retrieve(QUESTION, ents, True)
    ctx = "\n\n".join(f"[{i}] {d['text']}" for i, d in enumerate(docs, 1))
    ent = ", ".join(f"{e['text']} ({e['label']})" for e in ents) or "không có"
    return (
        f"Thực thể y tế nhận diện: {ent}\n\n"
        f"TÀI LIỆU THAM KHẢO:\n{ctx}\n\nCÂU HỎI: {QUESTION}"
    )


def main():
    bot = MedicalChatbot()
    user = build_user(bot)
    run_id = 0
    print(f"{'cấu hình':<34}{'prompt':>8}{'p_tok/s':>9}{'sinh':>6}{'g_tok/s':>9}{'nạp(s)':>8}")
    for rep in range(REPEATS):
        for cfg in CONFIGS:
            run_id += 1
            opts = {"temperature": 0.2, "num_predict": NUM_PREDICT, **cfg}
            r = ollama.chat(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": f"[{run_id}-{time.time():.0f}] {SYSTEM_PROMPT}"},
                    {"role": "user", "content": user},
                ],
                think=False,
                keep_alive=KEEP_ALIVE,
                options=opts,
            )
            pt = getattr(r, "prompt_eval_count", 0) or 0
            pd = (getattr(r, "prompt_eval_duration", 0) or 0) / 1e9
            gt = getattr(r, "eval_count", 0) or 0
            gd = (getattr(r, "eval_duration", 0) or 0) / 1e9
            ld = (getattr(r, "load_duration", 0) or 0) / 1e9
            print(
                f"{str(cfg):<34}{pt:>8}{(pt / pd if pd else 0):>9.1f}"
                f"{gt:>6}{(gt / gd if gd else 0):>9.1f}{ld:>8.1f}"
            )


if __name__ == "__main__":
    main()