import json
import random
import re
import sys
import unicodedata
from pathlib import Path

SEED = 42
N = 500
SRC = Path("data/processed/eval.jsonl")
OUT = Path("data/processed/eval_noisy.jsonl")

# dạng đúng -> các cách viết teencode / viết tắt hay gặp
TEEN = {
    "như thế nào": ["ntn", "nhu the nao"],
    "bao nhiêu": ["bn", "bao nhiu"],
    "bác sĩ": ["bs", "bsi"],
    "bệnh viện": ["bv"],
    "bình thường": ["bt"],
    "không": ["ko", "k", "hok", "hông"],
    "được": ["dc", "đc"],
    "bị": ["bi", "bj"],
    "gì": ["j"],
    "vậy": ["z"],
    "với": ["vs"],
    "rồi": ["r"],
    "tôi": ["t", "mik"],
    "mình": ["mik", "mk"],
    "bạn": ["b"],
    "phải": ["fai"],
    "những": ["nhg"],
    "người": ["ng"],
    "nhiều": ["nhiu"],
    "nhé": ["nhe"],
}


def strip_diacritics(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", text)


def add_teencode(text: str, rng: random.Random, p: float = 0.7) -> str:
    out = text.lower()
    for correct in sorted(TEEN, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(correct) + r"(?!\w)"
        out = re.sub(
            pattern,
            lambda m: rng.choice(TEEN[correct]) if rng.random() < p else m.group(0),
            out,
        )
    return out


def add_typos(text: str, rng: random.Random, p: float = 0.15) -> str:
    def fix(m):
        w = m.group(0)
        # chỉ sửa từ toàn chữ, đủ dài; bỏ qua số, liều lượng, mã thuốc
        if not w.isalpha() or len(w) < 4 or rng.random() >= p:
            return w
        i = rng.randrange(1, len(w) - 1)
        kind = rng.choice(["swap", "drop", "dup"])
        if kind == "swap":
            return w[:i] + w[i + 1] + w[i] + w[i + 2:]
        if kind == "drop":
            return w[:i] + w[i + 1:]
        return w[:i] + w[i] + w[i:]
    return re.sub(r"\w+", fix, text)


def main():
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    print("Các trường của dòng đầu:", list(rows[0].keys()))

    key = next((k for k in ("question", "query", "q", "text", "cau_hoi") if k in rows[0]), None)
    if key is None:
        print("Không tìm thấy trường câu hỏi, hãy gửi dòng trên cho Claude.")
        sys.exit(1)
    print("Dùng trường:", key, "| tổng số dòng:", len(rows))

    rng = random.Random(SEED)
    picked = rng.sample(rows, min(N, len(rows)))

    modes = {
        "nodiac": lambda s: strip_diacritics(s),
        "teen": lambda s: add_teencode(s, rng),
        "typo": lambda s: add_typos(s, rng),
        "mix": lambda s: strip_diacritics(add_typos(add_teencode(s, rng), rng)),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    changed = {m: 0 for m in modes}
    samples = {m: [] for m in modes}
    with OUT.open("w", encoding="utf-8") as f:
        for idx, row in enumerate(picked):
            orig = str(row[key]).strip()
            for mode, fn in modes.items():
                noisy = fn(orig)
                is_changed = noisy != orig.lower() if mode != "nodiac" else noisy != orig
                changed[mode] += int(is_changed)
                if len(samples[mode]) < 4:
                    samples[mode].append((orig, noisy))
                f.write(json.dumps(
                    {"id": idx, "mode": mode, "original": orig, "noisy": noisy},
                    ensure_ascii=False) + "\n")

    print("Đã ghi", OUT)
    for mode in modes:
        print(f"\n[{mode}] số câu thực sự bị thay đổi: {changed[mode]}/{len(picked)}")
        for o, n in samples[mode]:
            print("  gốc :", o[:110])
            print("  nhiễu:", n[:110])


if __name__ == "__main__":
    main()