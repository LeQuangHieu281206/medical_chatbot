import json
from pathlib import Path
from collections import Counter

root = Path("data/raw/ViMQ/data")

for split in ["train", "dev", "test"]:
    data = json.loads((root / f"{split}.json").read_text(encoding="utf-8"))
    lens = [len(d["sentence"].split()) for d in data]
    labels = Counter(l for d in data for _, _, l in d["seq_label"])
    no_ent = sum(1 for d in data if not d["seq_label"])
    print(f"\n== {split}: {len(data)} câu ==")
    print(f"độ dài token: trung bình {sum(lens)/len(lens):.1f}, lớn nhất {max(lens)}")
    print(f"câu không có thực thể: {no_ent}")
    print("số thực thể theo nhãn:", dict(labels))

# Kiểm tra span: in nguyên văn đoạn được gán nhãn (thử cả hai cách hiểu chỉ số kết thúc)
data = json.loads((root / "train.json").read_text(encoding="utf-8"))
print("\n== 8 ví dụ đầu: kiểm tra chỉ số kết thúc ==")
for d in data[:8]:
    toks = d["sentence"].split()
    print("\n", d["sentence"])
    for s, e, l in d["seq_label"]:
        print(f"  {l:20s} bao gồm: '{' '.join(toks[s:e+1])}'  |  không bao gồm: '{' '.join(toks[s:e])}'")