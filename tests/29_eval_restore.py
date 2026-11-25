import json
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.normalizer import QueryNormalizer, WORD_RE
from app.services.topic_filter import TopicFilter

SRC = Path("data/processed/eval_noisy.jsonl")
PASS_MAX, BLOCK_MIN = 0.12, 0.14


def pct(vals, q):
    return vals[min(len(vals) - 1, int(q * len(vals)))]


def zone_row(name, ds):
    ds = sorted(ds)
    n = len(ds)
    p = sum(d <= PASS_MAX for d in ds)
    b = sum(d > BLOCK_MIN for d in ds)
    print(f"{name:<16}{n:>5}{pct(ds, 0.5):>9.3f}{pct(ds, 0.95):>8.3f}"
          f"{100 * p / n:>8.1f}{100 * (n - p - b) / n:>8.1f}{100 * b / n:>8.1f}")


def main():
    t0 = time.time()
    norm = QueryNormalizer(rebuild="--rebuild" in sys.argv)
    print(f"Nạp từ điển: {time.time() - t0:.1f}s | số âm tiết: {len(norm.uni)} "
          f"| số khoá không dấu: {len(norm.forms)}")

    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    nodiac = [r for r in rows if r["mode"] == "nodiac"]
    mix = [r for r in rows if r["mode"] == "mix"]

    # 1. độ chính xác khôi phục dấu (chế độ nodiac)
    tok_tot = tok_ok = sent_ok = skipped = 0
    errors, worst, lat = Counter(), [], []
    for r in nodiac:
        t = time.perf_counter()
        out = norm.normalize(r["noisy"])
        lat.append(time.perf_counter() - t)
        o = WORD_RE.findall(unicodedata.normalize("NFC", r["original"]).lower())
        p = WORD_RE.findall(out.lower())
        if len(o) != len(p):
            skipped += 1
            continue
        alpha = [w for w in o if w.isalpha()]
        wrong = [(a, b) for a, b in zip(o, p) if a != b and a.isalpha()]
        tok_tot += len(alpha)
        tok_ok += len(alpha) - len(wrong)
        sent_ok += not wrong
        errors.update(wrong)
        worst.append((len(wrong), r["original"], out))

    n = len(nodiac) - skipped
    lat.sort()
    print(f"\n[Khôi phục dấu, chế độ nodiac] câu đánh giá: {n} (bỏ {skipped} câu lệch số từ)")
    print(f"  độ chính xác âm tiết: {100 * tok_ok / tok_tot:.2f}%")
    print(f"  câu khôi phục đúng hoàn toàn: {100 * sent_ok / n:.1f}%")
    print(f"  độ trễ median: {1000 * pct(lat, 0.5):.1f} ms, p95: {1000 * pct(lat, 0.95):.1f} ms")
    print("  15 nhầm lẫn hay gặp (gốc -> khôi phục):")
    for (a, b), c in errors.most_common(15):
        print(f"    {a} -> {b}: {c}")
    print("  5 câu nhiều lỗi nhất:")
    for k, o, out in sorted(worst, reverse=True)[:5]:
        print(f"    [{k} lỗi] gốc : {o[:100]}")
        print(f"             sau  : {out[:100]}")

    # 2. bộ lọc chủ đề trước và sau khi chuẩn hoá
    tf = TopicFilter()
    print(f"\n{'chế độ':<16}{'n':>5}{'median':>9}{'p95':>8}{'pass%':>8}{'gray%':>8}{'block%':>8}")
    for name, group in (("nodiac", nodiac), ("mix", mix)):
        zone_row(f"{name} (trước)", [tf._top1_distance(r["noisy"]) for r in group])
        zone_row(f"{name} (sau)", [tf._top1_distance(norm.normalize(r["noisy"])) for r in group])

    print("\n6 câu mix sau khi chuẩn hoá:")
    for r in mix[:6]:
        print("  nhiễu:", r["noisy"][:100])
        print("  sau  :", norm.normalize(r["noisy"])[:100])
        print("  gốc  :", r["original"][:100])


if __name__ == "__main__":
    main()