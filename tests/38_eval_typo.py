"""Đo tác dụng sửa lỗi chính tả: bản cũ (normalizer.py.pre_typo) so với bản mới.

- Chế độ nodiac / typo / mix: độ chính xác âm tiết, tỉ lệ câu đúng hoàn toàn, độ trễ.
- Hồi quy: câu gốc sạch có bị đổi từ nào không (càng gần 0 càng tốt).
"""
import importlib.machinery
import importlib.util
import json
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.normalizer import QueryNormalizer, WORD_RE  # noqa: E402

SRC = ROOT / "data/processed/eval_noisy.jsonl"
OLD = ROOT / "tests/fixtures/normalizer_pre_typo.py"


def load_old():
    loader = importlib.machinery.SourceFileLoader("normalizer_old", str(OLD))
    spec = importlib.util.spec_from_loader("normalizer_old", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod.QueryNormalizer()


def toks(text):
    return WORD_RE.findall(unicodedata.normalize("NFC", text).lower())


def pct(vals, q):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(q * len(vals)))]


def score(norm, rows, mode):
    """Trả về (độ chính xác âm tiết %, câu đúng %, median ms, p95 ms, ví dụ sai)."""
    tok_tot = tok_ok = sent_ok = n = 0
    lat, bad = [], []
    for r in rows:
        if r["mode"] != mode:
            continue
        t0 = time.perf_counter()
        out = norm.normalize(r["noisy"])
        lat.append(time.perf_counter() - t0)
        o, p = toks(r["original"]), toks(out)
        if len(o) != len(p):
            continue
        n += 1
        wrong = [(a, b) for a, b in zip(o, p) if a != b]
        alpha = sum(1 for a in o if a.isalpha())
        tok_tot += alpha
        tok_ok += alpha - sum(1 for a, _ in wrong if a.isalpha())
        if not wrong:
            sent_ok += 1
        elif len(bad) < 3:
            bad.append((r["noisy"], out, wrong[:3]))
    return (100 * tok_ok / max(tok_tot, 1), 100 * sent_ok / max(n, 1),
            1000 * pct(lat, 0.5), 1000 * pct(lat, 0.95), bad)


def clean_regression(norm, rows):
    """Đếm từ bị đổi trên câu gốc (đã đúng dấu) — càng thấp càng tốt."""
    tot = changed = sents = 0
    ex = []
    for r in rows:
        orig = r["original"]
        o, p = toks(orig), toks(norm.normalize(orig))
        if len(o) != len(p):
            continue
        sents += 1
        diff = [(a, b) for a, b in zip(o, p) if a != b]
        tot += sum(1 for a in o if a.isalpha())
        changed += len([1 for a, _ in diff if a.isalpha()])
        if diff and len(ex) < 8:
            ex.append((orig, norm.normalize(orig), diff[:3]))
    return 100 * changed / max(tot, 1), ex


def main():
    new, old = QueryNormalizer(), load_old()
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]

    print(f"{'chế độ':<8}{'bản':<6}{'âm tiết%':>10}{'câu đúng%':>11}{'p50ms':>8}{'p95ms':>8}")
    for mode in ("nodiac", "typo", "mix"):
        for name, norm in (("cũ", old), ("mới", new)):
            acc, sent, p50, p95, _ = score(norm, rows, mode)
            print(f"{mode:<8}{name:<6}{acc:>10.2f}{sent:>11.1f}{p50:>8.2f}{p95:>8.2f}")

    print("\n--- Hồi quy trên câu gốc sạch (từ bị đổi) ---")
    for name, norm in (("cũ", old), ("mới", new)):
        rate, ex = clean_regression(norm, rows)
        print(f"bản {name}: {rate:.3f}% từ bị đổi")
        if name == "mới":
            for o, out, d in ex:
                print(f"   gốc : {o[:90]}")
                print(f"   sau : {out[:90]}  {d}")

    print("\n--- Ví dụ còn sai (chế độ typo, bản mới) ---")
    for noisy, out, wrong in score(new, rows, "typo")[4]:
        print(f"  nhiễu: {noisy[:95]}")
        print(f"  sau  : {out[:95]}")
        print(f"  sai  : {wrong}")
    print("\n--- Ví dụ còn sai (chế độ mix, bản mới) ---")
    for noisy, out, wrong in score(new, rows, "mix")[4]:
        print(f"  nhiễu: {noisy[:95]}")
        print(f"  sau  : {out[:95]}")
        print(f"  sai  : {wrong}")


if __name__ == "__main__":
    main()
