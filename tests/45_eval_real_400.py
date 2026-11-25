"""Đánh giá trên bộ câu thật eval_chuan_hoa_cau_hoi_y_te.jsonl (400 dòng).

Mỗi dòng: {"noisy", "clean", "loai"}. Đo độ chính xác âm tiết và tỉ lệ câu
khôi phục hoàn toàn, tách theo loại nhiễu. Loại "sach" đo tỉ lệ sửa oan.
"""
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.normalizer import QueryNormalizer, WORD_RE  # noqa: E402

SRC = ROOT / "data/sources/eval_chuan_hoa_cau_hoi_y_te.jsonl"


def toks(t):
    return WORD_RE.findall(unicodedata.normalize("NFC", t).lower())


def main():
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    norm = QueryNormalizer()

    agg = defaultdict(lambda: {"tok": 0, "ok": 0, "sent": 0, "exact": 0,
                               "len": 0, "bad": []})
    for r in rows:
        clean, noisy, loai = r["clean"], r["noisy"], r.get("loai", "?")
        out = norm.normalize(noisy)
        g, p = toks(clean), toks(out)
        a = agg[loai]
        a["sent"] += 1
        if g == p:
            a["exact"] += 1
        if len(g) != len(p):
            a["len"] += 1
            continue
        wrong = [(x, y) for x, y in zip(g, p) if x != y]
        alpha = sum(1 for x in g if x.isalpha())
        a["tok"] += alpha
        a["ok"] += alpha - sum(1 for x, _ in wrong if x.isalpha())
        if wrong and len(a["bad"]) < 3:
            a["bad"].append((noisy, out, wrong[:3]))

    order = ["sach", "khong_dau", "viet_tat", "sai_chinh_ta", "sai_dau", "tron"]
    print(f"{'loại':<14}{'câu':>5}{'âm tiết%':>10}{'câu đúng%':>11}{'lệch số từ':>12}")
    tot = {"tok": 0, "ok": 0, "sent": 0, "exact": 0}
    for loai in order:
        if loai not in agg:
            continue
        a = agg[loai]
        print(f"{loai:<14}{a['sent']:>5}{100*a['ok']/max(a['tok'],1):>10.2f}"
              f"{100*a['exact']/a['sent']:>11.1f}{a['len']:>12}")
        if loai != "sach":
            for k in tot:
                tot[k] += a[k]

    print(f"\n{'TỔNG (bỏ sạch)':<14}{tot['sent']:>5}"
          f"{100*tot['ok']/max(tot['tok'],1):>10.2f}{100*tot['exact']/tot['sent']:>11.1f}")

    print("\n--- Ví dụ còn sai ---")
    for loai in order:
        for noisy, out, w in agg[loai]["bad"][:2]:
            print(f"  [{loai}] {noisy[:88]}")
            print(f"     -> {out[:88]}")
            print(f"     sai: {w}")
    s = agg.get("sach")
    if s:
        print(f"\nSửa oan trên câu sạch: {s['sent']-s['exact']}/{s['sent']} câu bị đổi")


if __name__ == "__main__":
    main()
