import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

KB = Path("data/processed/kb.jsonl")
WORD_RE = re.compile(r"\w+")


def toks(text):
    text = unicodedata.normalize("NFC", str(text)).lower()
    return [w for w in WORD_RE.findall(text) if w.isalpha()]


def main():
    q_cnt, a_cnt, example = Counter(), Counter(), {}
    with KB.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            q = str(row.get("question", ""))
            for w in toks(q):
                q_cnt[w] += 1
                example.setdefault(w, q[:90].replace("\n", " "))
            a_cnt.update(toks(row.get("answer", "")))

    # A: có trong câu hỏi (>=3 lần) nhưng không bao giờ xuất hiện trong câu trả lời
    a_list = [(w, n) for w, n in q_cnt.items() if n >= 3 and a_cnt[w] == 0]
    a_list.sort(key=lambda x: -x[1])
    print(f"A. Có ở câu hỏi, vắng ở câu trả lời: {len(a_list)} từ (top 80)")
    for w, n in a_list[:80]:
        print(f"  {w:<14}{n:>5} | {example[w]}")

    # B: từ ngắn (<=3 ký tự) phổ biến ở câu hỏi hơn hẳn câu trả lời
    b_list = [(w, n) for w, n in q_cnt.items()
              if len(w) <= 3 and n >= 5 and n / (a_cnt[w] + 1) >= 3]
    b_list.sort(key=lambda x: -x[1])
    print(f"\nB. Từ ngắn thiên về câu hỏi: {len(b_list)} từ (top 60)")
    for w, n in b_list[:60]:
        print(f"  {w:<14}{n:>5} (trong câu trả lời: {a_cnt[w]}) | {example[w]}")


if __name__ == "__main__":
    main()