"""End-to-end: chuẩn hoá câu hỏi có giúp truy xuất đúng tài liệu không?

Ground truth lấy trực tiếp từ kb.jsonl (chính là dữ liệu đã nạp vào ChromaDB),
nên câu hỏi vàng chắc chắn có trong chỉ mục -> trần hit@k xấp xỉ 100%.

Với mỗi câu vàng, tạo 4 biến thể (sạch / typo / không dấu / trộn), truy xuất top-k
2 lần: (a) nguyên văn biến thể, (b) sau khi chuẩn hoá. Đo hit@k và MRR.
"""
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import chromadb  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.services.normalizer import (QueryNormalizer, WORD_RE,  # noqa: E402
                                     strip_diacritics)
from app.services.topic_filter import COLLECTION, DB_PATH, EMBED_MODEL  # noqa: E402

RNG = random.Random(11)
N = 150
K = 5

TEEN_SWAP = {"bác sĩ": "bs", "bệnh viện": "bv", "xét nghiệm": "xn",
             "không": "ko", "được": "đc", "nhiều": "nhìu", "cũng": "cũg",
             "nhưng": "nhug", "mình": "mik", "phải": "fai", "bệnh": "bịnh",
             "đang": "đag", "muốn": "mún", "trước": "trc", "với": "vs"}


def ws(s):
    return re.sub(r"\s+", " ", s).strip()


def key(s, n=50):
    s = ws(strip_diacritics(unicodedata.normalize("NFC", s).lower()))
    return s[:n]


def add_typos(text, n=2):
    for _ in range(n):
        ms = list(WORD_RE.finditer(text))
        idx = [i for i, m in enumerate(ms) if m.group(0).isalpha() and len(m.group(0)) >= 4]
        if not idx:
            break
        m = ms[RNG.choice(idx)]
        w = m.group(0)
        op = RNG.choice("disc")
        try:
            if op == "d" and len(w) >= 4:
                i = RNG.randrange(len(w) - 1) + 1
                bad = w[:i] + w[i + 1:]
            elif op == "i":
                i = RNG.randrange(len(w) - 1) + 1
                bad = w[:i] + w[i - 1] + w[i:]
            elif op == "s" and len(w) >= 3:
                i = RNG.randrange(len(w) - 1)
                bad = w[:i] + w[i + 1] + w[i] + w[i + 2:]
            else:
                i = RNG.randrange(len(w) - 1) + 1
                bad = w[:i] + RNG.choice("nhtcsmv") + w[i + 1:]
        except ValueError:
            continue
        text = text[:m.start()] + bad + text[m.end():]
    return text


def add_teen(text):
    for full, short in TEEN_SWAP.items():
        if full in text.lower():
            return re.sub(re.escape(full), short, text, count=1, flags=re.I)
    return text


def variant(text, mode):
    if mode == "clean":
        return text
    if mode == "typo":
        return add_typos(text)
    if mode == "nodiac":
        return strip_diacritics(text)
    return add_teen(add_typos(text))


def main():
    seen, rows = set(), []
    for line in (ROOT / "data/processed/kb.jsonl").open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        q = ws(r.get("question") or "")
        k = key(q)
        if 15 < len(q) < 200 and k and k not in seen:
            seen.add(k)
            rows.append(r)
        if len(rows) >= N * 3:
            break
    RNG.shuffle(rows)
    rows = rows[:N]

    norm = QueryNormalizer()
    model = SentenceTransformer(EMBED_MODEL)
    col = chromadb.PersistentClient(path=DB_PATH).get_collection(COLLECTION)

    modes = ["clean", "typo", "nodiac", "mix"]
    stats = {m: {"raw": 0, "norm": 0, "rr_raw": 0.0, "rr_norm": 0.0, "chg": 0}
             for m in modes}
    n = 0
    bad_ex = []

    for r in rows:
        gold = key(r["question"])
        for mode in modes:
            q = ws(variant(r["question"], mode))
            qn = ws(norm.normalize(q))
            ranks = {}
            for tag, text in (("raw", q), ("norm", qn)):
                emb = model.encode([f"query: {text}"], normalize_embeddings=True).tolist()
                res = col.query(query_embeddings=emb, n_results=K, include=["documents"])
                docs = (res.get("documents") or [[]])[0]
                rank = next((i + 1 for i, d in enumerate(docs) if gold in key(d, 120)), None)
                ranks[tag] = rank
                if rank:
                    stats[mode][tag] += 1
                    stats[mode]["rr_" + tag] += 1.0 / rank
            if ranks["raw"] and not ranks["norm"]:
                stats[mode]["chg"] -= 1
            elif ranks["norm"] and not ranks["raw"]:
                stats[mode]["chg"] += 1
            elif mode != "clean" and not ranks["raw"] and not ranks["norm"] and len(bad_ex) < 4:
                bad_ex.append((mode, q, qn))
        n += 1

    print(f"Câu hỏi vàng: {n}, k={K}, embed={EMBED_MODEL}\n")
    print(f"  {'biến thể':<10}{'hit@5 thô':>11}{'hit@5 chuẩn':>13}{'MRR thô':>10}"
          f"{'MRR chuẩn':>11}{'Δ hit':>8}")
    for m in modes:
        s = stats[m]
        print(f"  {m:<10}{100*s['raw']/n:>10.1f}%{100*s['norm']/n:>12.1f}%"
              f"{s['rr_raw']/n:>10.3f}{s['rr_norm']/n:>11.3f}{s['chg']:>+8d}")

    if bad_ex:
        print("\n  Vẫn trượt sau chuẩn hoá:")
        for mode, q, qn in bad_ex:
            print(f"   [{mode}] {q[:75]}")
            print(f"          -> {qn[:75]}")


if __name__ == "__main__":
    main()
