import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.pipeline import MedicalChatbot

QUESTION = "Trẻ bị sốt cao co giật thì xử lý thế nào?"

bot = MedicalChatbot()
bot.warmup()

t0 = time.perf_counter()
first_model_line = None
for ev in bot.ask_stream(QUESTION):
    now = time.perf_counter() - t0
    if ev["type"] == "meta":
        ents = "; ".join(f"{e['text']} [{e['label']}]" for e in ev["entities"]) or "-"
        print(f"[{now:5.1f}s] lọc chủ đề: {ev['topic'].zone} | thực thể: {ents}\n")
    elif ev["type"] == "static":
        print(ev["text"], end="", flush=True)
    elif ev["type"] == "text":
        if first_model_line is None and ev["text"].strip():
            first_model_line = now
            print(f"\n[{now:5.1f}s] dòng đầu tiên của qwen]")
        print(ev["text"], end="", flush=True)
    elif ev["type"] == "final":
        print(f"\n\n[{now:5.1f}s] xong | thống kê qwen: {ev['stats']}")
        for s in ev["sources"]:
            print(f"  nguồn d={s['distance']:.3f} | {s['question'][:70]}")