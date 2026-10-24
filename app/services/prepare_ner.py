import json
from pathlib import Path
from collections import Counter

SRC = Path("data/raw/ViMQ/data")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)


def convert(item):
    words = item["sentence"].split()
    tokens, word_start = [], []
    for w in words:
        word_start.append(len(tokens))
        tokens.extend(s for s in w.split("_") if s)
    word_start.append(len(tokens))

    labels = ["O"] * len(tokens)
    conflicts = 0
    for s, e, lab in item["seq_label"]:
        if e + 1 >= len(word_start):
            conflicts += 1
            continue
        a, b = word_start[s], word_start[e + 1]
        if b <= a or any(x != "O" for x in labels[a:b]):
            conflicts += 1
            continue
        labels[a] = f"B-{lab}"
        for i in range(a + 1, b):
            labels[i] = f"I-{lab}"
    return tokens, labels, conflicts


def decode(tokens, labels):
    spans, start, cur = [], None, None
    for i, lab in enumerate(labels + ["O"]):
        if lab.startswith("B-") or lab == "O" or (cur and lab[2:] != cur):
            if start is not None:
                spans.append((start, i, cur))
                start, cur = None, None
        if lab.startswith("B-"):
            start, cur = i, lab[2:]
    return spans


label_set = set()
for split in ["train", "dev", "test"]:
    data = json.loads((SRC / f"{split}.json").read_text(encoding="utf-8"))
    n_conf, n_orig, n_dec, max_len = 0, 0, 0, 0
    rows = []
    for item in data:
        tokens, labels, c = convert(item)
        n_conf += c
        n_orig += len(item["seq_label"])
        n_dec += len(decode(tokens, labels))
        max_len = max(max_len, len(tokens))
        label_set.update(labels)
        rows.append({"tokens": tokens, "labels": labels})
    with open(OUT / f"ner_{split}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{split}: {len(rows)} câu | thực thể gốc {n_orig}, "
          f"giải mã lại {n_dec}, bỏ vì chồng lấn/lỗi {n_conf} | "
          f"số âm tiết dài nhất {max_len}")

order = ["O"] + sorted(l for l in label_set if l != "O")
(OUT / "ner_labels.json").write_text(
    json.dumps(order, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nNhãn:", order)

# In 3 ví dụ để kiểm tra bằng mắt
rows = [json.loads(l) for l in open(OUT / "ner_train.jsonl", encoding="utf-8")][:3]
for r in rows:
    print("\n", " ".join(r["tokens"]))
    for s, e, lab in decode(r["tokens"], r["labels"]):
        print(f"  {lab:20s} '{' '.join(r['tokens'][s:e])}'")