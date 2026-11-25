"""Dò sitemap mirror Dược thư (Bạch Mai) để lập danh sách hoạt chất dùng được.

Bước 1 của việc mở rộng KB thuốc: biết trang nào thật sự là chuyên luận và có đủ
5 khía cạnh (chỉ định / chống chỉ định / thận trọng / ADR / tương tác) trước khi
sinh QA. Không sinh dữ liệu, chỉ lập danh mục + cache HTML để build lại offline.

Chạy:
    .venv/bin/python scripts/build_drug_index.py                # dò toàn bộ slug ứng viên
    .venv/bin/python scripts/build_drug_index.py --limit 20     # chạy thử
    .venv/bin/python scripts/build_drug_index.py --min-facets 5 # chỉ lấy trang đủ 5 khía cạnh

Kết quả:
    data/sources/duocthu/index.jsonl      # {name, slug, url, facets, missing, cached}
    data/sources/duocthu/raw/<slug>.html  # HTML gốc, để build lại không cần mạng
    data/audit/duocthu_rejected.csv       # slug bị loại + lý do
"""
import argparse
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_drug_qa as bd  # noqa: E402  (dùng lại fetch/sections/_parse)

BASE = "https://chanthuongvacotsong.bachmai.gov.vn"
SITEMAPS = [f"{BASE}/post-sitemap{suffix}.xml" for suffix in ("", "2", "3")]
OUT_DIR = ROOT / "data/sources/duocthu"
RAW_DIR = OUT_DIR / "raw"
INDEX = OUT_DIR / "index.jsonl"
REJECTED = ROOT / "data/audit/duocthu_rejected.csv"

FACETS = ("indication", "contraindication", "caution", "adr", "interaction")
SLUG_MAX = 25
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)


def get(url: str, timeout: int = 25) -> str:
    req = Request(url, headers={"User-Agent": "medical-chatbot-databuild/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def sitemap_slugs() -> list[str]:
    slugs = []
    for sm in SITEMAPS:
        try:
            xml = get(sm)
        except Exception as exc:  # noqa: BLE001
            print(f"  bỏ qua {sm}: {type(exc).__name__}")
            continue
        slugs += [urlparse(u).path.strip("/") for u in re.findall(r"<loc>([^<]+)</loc>", xml)]
    return slugs


def candidates(slugs: list[str]) -> list[str]:
    """Slug một tầng, ngắn, không chứa số — vùng chuyên luận thuốc của site."""
    return sorted({s for s in slugs
                   if 0 < len(s) <= SLUG_MAX and "/" not in s and not any(c.isdigit() for c in s)})


def page_name(html: str) -> str:
    m = H1_RE.search(html)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def probe(slug: str, cache: bool) -> dict:
    path = RAW_DIR / f"{slug}.html"
    try:
        if path.exists():
            html = path.read_text(encoding="utf-8")
        else:
            html = get(f"{BASE}/{slug}/")
            if cache:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(html, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return {"slug": slug, "url": f"{BASE}/{slug}/", "error": type(exc).__name__}

    secs = bd.sections(bd._parse(html))
    have = [k for k in FACETS if secs.get(k)]
    return {
        "slug": slug,
        "url": f"{BASE}/{slug}/",
        "name": page_name(html),
        "facets": have,
        "missing": [k for k in FACETS if k not in have],
        "cached": path.exists(),
    }


def main():
    ap = argparse.ArgumentParser(description="Lập danh mục chuyên luận thuốc từ sitemap")
    ap.add_argument("--limit", type=int, default=0, help="chỉ dò N slug đầu (chạy thử)")
    ap.add_argument("--min-facets", type=int, default=4,
                    help="số khía cạnh tối thiểu để giữ (mặc định 4)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-cache", action="store_true", help="không ghi HTML gốc")
    args = ap.parse_args()

    print("Đang đọc sitemap...")
    slugs = candidates(sitemap_slugs())
    if args.limit:
        slugs = slugs[: args.limit]
    print(f"Ứng viên: {len(slugs)} slug một tầng, ≤ {SLUG_MAX} ký tự, không chứa số")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda s: probe(s, not args.no_cache), slugs))

    usable = [r for r in rows if "error" not in r and len(r["facets"]) >= args.min_facets]
    rejected = [r for r in rows if r not in usable]
    unnamed = sum(1 for r in usable if not r["name"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                             for r in sorted(usable, key=lambda x: x["slug"])),
                     encoding="utf-8")

    REJECTED.parent.mkdir(parents=True, exist_ok=True)
    with REJECTED.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["slug", "url", "lý do", "khía cạnh có", "khía cạnh thiếu"])
        for r in rejected:
            if "error" in r:
                w.writerow([r["slug"], r["url"], f"tải lỗi {r['error']}", "", ""])
            else:
                w.writerow([r["slug"], r["url"], "không phải chuyên luận thuốc",
                            ",".join(r["facets"]), ",".join(r["missing"])])

    print(f"\nĐủ ≥{args.min_facets} khía cạnh: {len(usable)}/{len(rows)} "
          f"→ tối đa {len(usable) * len(FACETS)} dòng QA")
    print(f"  đủ cả 5: {sum(1 for r in usable if len(r['facets']) == 5)}")
    print(f"  thiếu tên (h1): {unnamed}")
    print(f"  loại: {len(rejected)} (xem {REJECTED.relative_to(ROOT)})")
    print(f"  danh mục: {INDEX.relative_to(ROOT)}")
    if not args.no_cache:
        print(f"  HTML gốc: {RAW_DIR.relative_to(ROOT)}/ ({len(list(RAW_DIR.glob('*.html')))} file)")


if __name__ == "__main__":
    main()
