import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.topic_filter import TopicFilter

SRC = Path("data/processed/eval_noisy.jsonl")
PASS_MAX, BLOCK_MIN = 0.12, 0.14   # ngưỡng của topic_filter.py


def pct(sorted_vals, q):
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))]


def zone(d):
    if d <= PASS_MAX:
        return "pass"
    if d <= BLOCK_MIN:
        return "gray"
    return "block"


def main():
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    tf = TopicFilter()

    # khoảng cách của câu gốc (mỗi id một lần)
    orig_d = {}
    for r in rows:
        if r["id"] not in orig_d:
            orig_d[r["id"]] = tf._top1_distance(r["original"])

    results = {"original": [(i, d, None, None) for i, d in orig_d.items()]}
    for r in rows:
        noisy, orig = r["noisy"], r["original"]
        # bỏ câu không thực sự bị đổi ở chế độ teen và typo
        if r["mode"] in ("teen", "typo") and noisy == orig.lower():
            continue
        if r["mode"] == "typo" and noisy == orig:
            continue
        d = tf._top1_distance(noisy)
        results.setdefault(r["mode"], []).append((r["id"], d, noisy, orig))

    print(f"{'chế độ':<10}{'n':>5}{'median':>9}{'p95':>8}{'pass%':>8}{'gray%':>8}{'block%':>8}{'Δ TB so với gốc':>18}")
    for mode in ("original", "nodiac", "teen", "typo", "mix"):
        items = results.get(mode, [])
        if not items:
            continue
        ds = sorted(x[1] for x in items)
        n = len(ds)
        z = {"pass": 0, "gray": 0, "block": 0}
        for d in ds:
            z[zone(d)] += 1
        delta = sum(x[1] - orig_d[x[0]] for x in items) / n
        print(f"{mode:<10}{n:>5}{pct(ds, 0.5):>9.3f}{pct(ds, 0.95):>8.3f}"
              f"{100 * z['pass'] / n:>8.1f}{100 * z['gray'] / n:>8.1f}"
              f"{100 * z['block'] / n:>8.1f}{delta:>18.3f}")

    print("\n8 câu mix bị đẩy xa nhất:")
    worst = sorted(results["mix"], key=lambda x: -x[1])[:8]
    for _, d, noisy, orig in worst:
        print(f"  d={d:.3f} | {noisy[:90]}")
        print(f"          gốc: {orig[:90]}")


if __name__ == "__main__":
    main()