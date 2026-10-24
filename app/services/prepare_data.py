import json
import random
import re
from pathlib import Path

from datasets import load_dataset

OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)


def clean(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def strip_question(q: str) -> str:
    q = clean(q)
    q = re.sub(r"^(xin )?chào\s+(bác sĩ|bác sỹ|bs)[\s,!.]*", "", q, flags=re.I)
    q = re.sub(r"^(ạ|dạ)\s*[\n,.!]+\s*", "", q, flags=re.I)
    q = re.sub(r"[\s,]*(em|cháu|con|tôi|mình)\s+(xin\s+)?cảm ơn( bác sĩ)?[\s!.]*$", "", q, flags=re.I)
    return q.strip()


def strip_answer(a: str) -> str:
    a = clean(a)
    a = re.sub(r"^(xin )?chào\s+(em|anh|chị|anh/chị|bạn|cô|chú|bác)[\s,!.]*", "", a, flags=re.I)
    a = re.sub(r"^với câu hỏi[^\n]*bác sĩ xin (trả lời|giải đáp)[^\n]*\n?", "", a, flags=re.I)
    a = re.sub(
        r"để trả lời câu hỏi (của bạn|trên)[^.\n]*?bác sĩ (xin )?(giải đáp|trả lời)[^.\n:]*[:.]?\s*",
        "", a, flags=re.I,
    )
    a = re.sub(r"[\s]*(trân trọng|thân ái|thân mến)[^\n]{0,30}$", "", a, flags=re.I)
    return a.strip()

def make(source, q, a, link=""):
    return {
        "source": source,
        "question": strip_question(q),
        "answer": strip_answer(a),
        "link": link,
    }


def valid(r):
    return len(r["question"]) >= 10 and len(r["answer"]) >= 30


def stats(name, rows):
    n = len(rows)
    if n == 0:
        print(name, ": rỗng")
        return
    avg_q = sum(len(r["question"]) for r in rows) // n
    avg_a = sum(len(r["answer"]) for r in rows) // n
    long_ = sum(len(r["question"]) + len(r["answer"]) > 800 for r in rows)
    print(f"{name}: {n} dòng | TB câu hỏi {avg_q} ký tự | TB trả lời {avg_a} ký tự | "
          f"{long_} dòng dài hơn 800 ký tự ({long_ * 100 // n}%)")


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


kb, ev = [], []

vi = load_dataset("tarudesu/ViHealthQA")
for split in ("train", "validation"):
    kb += [make("ViHealthQA", r["question"], r["answer"], r["link"]) for r in vi[split]]
ev += [make("ViHealthQA", r["question"], r["answer"], r["link"]) for r in vi["test"]]

hn = load_dataset("hungnm/vietnamese-medical-qa")["train"]
hn_rows = [make("vietnamese-medical-qa", r["question"], r["answer"]) for r in hn]
random.Random(42).shuffle(hn_rows)
ev += hn_rows[:300]
kb += hn_rows[300:]

print("Trước khi lọc: kb =", len(kb), "| eval =", len(ev))
kb = [r for r in kb if valid(r)]
ev = [r for r in ev if valid(r)]

# bỏ trùng câu hỏi, và bỏ khỏi kb mọi câu hỏi nằm trong tập đánh giá
eval_qs = {r["question"].lower() for r in ev}
seen, kb_dedup = set(), []
for r in kb:
    key = r["question"].lower()
    if key in seen or key in eval_qs:
        continue
    seen.add(key)
    kb_dedup.append(r)
kb = kb_dedup

stats("kb", kb)
stats("eval", ev)

write_jsonl(OUT / "kb.jsonl", kb)
write_jsonl(OUT / "eval.jsonl", ev)

print("\nMẫu sau khi làm sạch (vietnamese-medical-qa):")
for r in [x for x in kb if x["source"] == "vietnamese-medical-qa"][:2]:
    print("Q:", r["question"])
    print("A:", r["answer"])
    print("-" * 40)