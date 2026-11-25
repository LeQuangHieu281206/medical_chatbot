"""Đo tác động của việc gõ sai tên thuốc: chuẩn hoá + truy hồi còn đúng không.

Với mỗi hoạt chất trong KB thuốc, sinh các kiểu gõ sai thường gặp rồi kiểm:
  1. `normalizer.normalize` có sửa được tên thuốc về đúng không
  2. truy hồi top-1 có trỏ đúng chuyên luận của thuốc đó không

Chỉ ĐỌC dữ liệu + vector DB, không ghi gì.

Chạy:
    .venv/bin/python tests/45_test_drug_typos.py
    .venv/bin/python tests/45_test_drug_typos.py --n 12
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import chromadb  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.services.normalizer import QueryNormalizer  # noqa: E402

DB_PATH = ROOT / "app/db/chroma_db"
COLLECTION = "medical_kb"
EMBED_MODEL = "intfloat/multilingual-e5-small"
KB_DRUGS = ROOT / "data/processed/kb_drugs_full.jsonl"

TEMPLATES = [
    "{name} tương tác với thuốc nào?",
    "tác dụng phụ của {name}",
    "uống {name} có sao không",
    "{name}",                        # câu cụt: chỉ tên thuốc mang nghĩa
    "có nên uống {name} hàng ngày",
]

# Gõ sai kiểu người Việt hay gặp: nuốt chữ, gõ đôi, đảo chữ, đọc thành vần,
# viết tắt trong đơn thuốc.
TEENCODE = {
    "paracetamol": "pcm",
    "amoxicilin": "amox",
    "ibuprofen": "ibu",
    "omeprazol": "omep",
    "metformin": "metfomin",
}
SLANG = {
    "paracetamol": "paracetamon",
    "amoxicilin": "amoxixilin",
    "ibuprofen": "ibuprofene",
    "metformin": "metformine",
    "omeprazol": "omeprazole",
    "salbutamol": "salbutamone",
    "prednisolon": "prednisolone",
    "diclofenac": "diclofenacq",
    "cetirizin": "cetirizinne",
    "losartan": "losartin",
}


def drop_letter(name: str) -> str:
    return name[:-2] + name[-1] if len(name) > 5 else name[:-1]


def double_letter(name: str) -> str:
    return name[:3] + name[3] + name[3:]


def swap_letters(name: str) -> str:
    i = max(2, len(name) // 2 - 1)
    return name[:i] + name[i + 1] + name[i] + name[i + 2:]


def load_drugs():
    rows = [json.loads(l) for l in KB_DRUGS.open(encoding="utf-8") if l.strip()]
    name_of = {}
    for r in rows:
        url = r["link"]
        slug = urlparse(url).path.strip("/").split("/")[-1]
        name = r["question"].split(" được chỉ định")[0].split(" tương tác")[0] \
            .split("Ai không nên dùng ")[-1].split(" cần thận trọng")[0] \
            .split("Tác dụng phụ thường gặp của ")[-1].split(" là gì")[0]
        name_of[slug] = name.strip()
    return name_of


def main():
    ap = argparse.ArgumentParser(description="Đo ảnh hưởng của gõ sai tên thuốc")
    ap.add_argument("--n", type=int, default=24, help="số hoạt chất đem kiểm")
    args = ap.parse_args()

    name_of = load_drugs()
    # Lấy cả thuốc có biến thể viết tắt/đọc chệch, rồi bù cho đủ số lượng
    needed = {s for s, n in name_of.items() if n.lower() in SLANG or n.lower() in TEENCODE}
    slugs = sorted(needed)[: args.n]
    slugs += [s for s in sorted(name_of) if s not in slugs][: max(0, args.n - len(slugs))]
    norm = QueryNormalizer()
    model = SentenceTransformer(EMBED_MODEL)
    col = chromadb.PersistentClient(path=str(DB_PATH)).get_collection(COLLECTION)

    def slug_of(meta):
        return urlparse(meta.get("link") or "").path.strip("/").split("/")[-1]

    stats = defaultdict(Counter)     # kiểu gõ -> {"fixed": n, "hit": n, "total": n}
    examples = []

    for slug in slugs:
        name = name_of[slug].lower()
        variants = {"đúng": name}
        for label, fn in (("nuốt chữ", drop_letter), ("gõ đôi", double_letter),
                          ("đảo chữ", swap_letters)):
            v = fn(name)
            if v != name:
                variants[label] = v
        if name in SLANG:
            variants["đọc chệch"] = SLANG[name]
        if name in TEENCODE:
            variants["viết tắt"] = TEENCODE[name]

        for label, wrong in variants.items():
            stats[label]["total"] += 1
            fixed = norm.normalize(wrong)
            if name in fixed.lower():
                stats[label]["fixed"] += 1
            for tpl in TEMPLATES:
                q = tpl.format(name=wrong)
                for tag, text in (("hit", q), ("hit_norm", norm.normalize(q))):
                    emb = model.encode([f"query: {text}"], normalize_embeddings=True).tolist()
                    res = col.query(query_embeddings=emb, n_results=1)
                    ok = slug_of(res["metadatas"][0][0]) == slug
                    stats[label][tag] += ok
                    if tag == "hit_norm" and not ok and len(examples) < 5:
                        examples.append((label, text, res["metadatas"][0][0]["question"][:60]))
                stats[label]["queries"] += 1

    print(f"Kiểm {len(slugs)} hoạt chất × {len(TEMPLATES)} mẫu câu\n")
    print(f"{'kiểu gõ':<12}{'sửa được':>10}{'truy hồi thô':>14}{'sau chuẩn hoá':>15}{'câu':>7}")
    for label, c in stats.items():
        print(f"{label:<12}{c['fixed']:>6}/{c['total']:<4}"
              f"{100 * c['hit'] / c['queries']:>13.0f}%"
              f"{100 * c['hit_norm'] / c['queries']:>14.0f}%{c['queries']:>8}")
    print("\nVí dụ chuẩn hoá (câu chỉ có tên thuốc gõ sai):")
    shown = 0
    for slug in slugs:
        name = name_of[slug].lower()
        for label, wrong in (("nuốt chữ", drop_letter(name)),
                             ("đảo chữ", swap_letters(name)),
                             ("đọc chệch", SLANG.get(name)),
                             ("viết tắt", TEENCODE.get(name))):
            if not wrong or wrong == name:
                continue
            print(f"  [{label}] {wrong:<24} -> {norm.normalize(wrong)}")
            shown += 1
            if shown >= 8:
                break
        if shown >= 8:
            break

    if examples:
        print("\nVí dụ truy hồi sai:")
        for label, q, got in examples:
            print(f"  [{label}] {q[:50]:<52} -> {got}")


if __name__ == "__main__":
    main()
