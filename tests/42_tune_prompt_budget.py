"""Chọn ngân sách ký tự cho tài liệu đưa vào prompt.

Đo trực tiếp đầu ra của MedicalChatbot.retrieve() (đúng thứ đi vào prompt) trên câu hỏi
từ eval.jsonl: độ phủ từ của đáp án vàng, tổng ký tự, số tài liệu.

Chạy: .venv/bin/python tests/42_tune_prompt_budget.py
"""
import json
import random
import re
import statistics as st
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.services.pipeline as P
from app.services.pipeline import MedicalChatbot

EVAL = Path("data/processed/eval.jsonl")
WORD_RE = re.compile(r"\w+", re.UNICODE)

# (tên, MAX_QA_CHARS, MAX_DOC_CHARS, QUOTA_QA, QUOTA_ENCYC, MAX_CONTEXT_CHARS)
CONFIGS = [
    ("hiện tại 350", 350, 800, 1, 2, 3000),
    ("QA 700", 700, 800, 1, 2, 3000),
    ("QA 900", 900, 800, 1, 2, 3000),
    ("QA 700 + enc 700", 700, 700, 1, 2, 3000),
    ("QA 1200, enc 900", 1200, 900, 1, 2, 3400),
]


def toks(text):
    return set(WORD_RE.findall(unicodedata.normalize("NFC", text or "").lower()))


def apply(cfg):
    _, qa, doc, q_qa, q_en, total = cfg
    P.MAX_QA_CHARS = qa
    P.MAX_DOC_CHARS = doc
    P.QUOTA_QA = q_qa
    P.QUOTA_ENCYC = q_en
    P.MAX_CONTEXT_CHARS = total


def main():
    rows = [json.loads(l) for l in EVAL.open(encoding="utf-8") if l.strip()]
    random.Random(42).shuffle(rows)
    rows = rows[:150]
    print(f"Đo trên {len(rows)} câu hỏi\n")

    bot = MedicalChatbot()
    if bot.encyc is None:
        print("CẢNH BÁO: chưa có collection bách khoa, chỉ đo được phần hỏi đáp")

    print(f"{'cấu hình':<20}{'ký tự TB':>10}{'p95 ký tự':>11}{'số tài liệu':>13}"
          f"{'phủ đáp án':>12}")
    results = []
    for cfg in CONFIGS:
        apply(cfg)
        chars, covs, ndocs = [], [], []
        for r in rows:
            docs = bot.retrieve(r["question"], [], use_entities=False)
            text = "\n".join(d["text"] for d in docs)
            chars.append(len(text))
            ndocs.append(len(docs))
            gold = toks(r["answer"])
            covs.append(len(gold & toks(text)) / len(gold) if gold else 0.0)
        results.append((cfg[0], st.mean(covs), st.mean(chars), st.mean(ndocs)))
        print(f"{cfg[0]:<20}{st.mean(chars):>10.0f}"
              f"{sorted(chars)[int(0.95 * len(chars)) - 1]:>11}"
              f"{st.mean(ndocs):>13.1f}{st.mean(covs):>12.3f}")

    best = max(results, key=lambda r: r[1])
    print(f"\nTối ưu theo độ phủ/1 ký tự prompt: {best[0]}")
    for name, cov, ch, nd in results:
        print(f"  {name:<20} phủ {cov:.3f} | {ch:.0f} ký tự | hiệu quả {cov / ch * 1000:.2f}‰")


if __name__ == "__main__":
    main()
