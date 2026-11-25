"""Dựng câu hỏi-đáp từ bài viết Vinmec cho hai chủ đề còn mỏng: vaccine, dinh dưỡng.

Vì sao cần: `kb.jsonl` chỉ có 85 câu vaccine và 99 câu dinh dưỡng (ngưỡng hợp đồng
là 400/chủ đề), trong khi hai bộ dữ liệu gốc đã dùng hết. Nguồn này có câu hỏi thật
của người bệnh và bác sĩ trả lời, robots.txt cho phép đọc.

Cách làm: sitemap → lọc slug theo chủ đề → tải bài (có cache) → lấy `h1` làm câu hỏi,
phần thân bài làm đáp án. Mỗi dòng giữ `link` để truy vết và ghi nguồn ở UI.

Chạy:
    .venv/bin/python scripts/build_vinmec_qa.py                  # tải + dựng, ghi file
    .venv/bin/python scripts/build_vinmec_qa.py --limit 50       # thử nhanh
    .venv/bin/python scripts/build_vinmec_qa.py --no-fetch       # chỉ dùng cache sẵn

Ghi ra: data/processed/kb_vinmec.jsonl (không ghi đè file nào đang dùng).
"""
import argparse
import html as htmllib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "https://www.vinmec.com"
SITEMAP = f"{BASE}/sitemap.xml"
CACHE = ROOT / "data/sources/vinmec/html"
INDEX = ROOT / "data/sources/vinmec/index.jsonl"
OUT = ROOT / "data/processed/kb_vinmec.jsonl"

UA = "Mozilla/5.0 (X11; Linux x86_64) medical-chatbot-research/1.0"
ANSWER_MIN = 150        # dưới ngưỡng này thì bài không trả lời được gì
ANSWER_MAX = 1900       # để validator --strict còn qua (trần 2000)
TIMEOUT = 30

# --- chọn bài ------------------------------------------------------------
# So khớp trên dạng đã bỏ dấu và đổi "-" thành " " để cùng một mẫu dùng được cho
# cả slug lẫn tiêu đề có dấu ("viêm gan B" và "viem-gan-b").
VACCINE_RE = re.compile(
    r"\b(vac ?xin|vaccine|tiem chung|tiem phong|tiem ngua|mui tiem|"
    r"viem gan|benh soi|tiem soi|rubella|quai bi|uon van|bach hau|ho ga|"
    r"nao mo cau|phoi cau|thuy dau|rota ?virus|rota|hpv|zona|benh dai|tiem dai|"
    r"sot xuat huyet|khang the|mien dich)\b"
)
NUTRITION_RE = re.compile(
    r"\b(dinh duong|thuc pham|thuc don|thuc an|vitamin|khoang chat|chat dinh duong|"
    r"protein|canxi|thieu sat|bo sung sat|omega|probiotic|sua me|sua cong thuc|"
    r"beo phi|thua can|tang can|giam can|suy dinh duong|an chay|che do an|"
    r"khau phan|do an|do uong|nuoc uong|trai cay|rau cu|chat beo|chat xo|dam)\b"
)
DENY_RE = re.compile(
    r"\b(uu dai|khuyen mai|bang gia|bao gia|goi kham|dat lich|chi phi|bao hiem|"
    r"tuyen dung|su kien|chuyen gia|bac si|trung tam|co so|phong kham|he thong|"
    r"thiet bi|hoi nghi|hoi thao|khach hang|hop tac|nhan vien|quang cao)\b"
)

# chỉ giữ bài nói về chính việc tiêm chủng (không lấy bài về bệnh)
STRONG_VACCINE_RE = re.compile(r"\b(tiem|vac xin|vaccine|mui tiem)\b")

# dòng rác của khung trang (không phải nội dung y khoa)
JUNK_LINE_RE = re.compile(
    r"^(cố vấn chuyên môn|đặt lịch khám|xem chi tiết|☰|mục lục|chia sẻ|bình luận|"
    r"bài viết được tư vấn|tham khảo thêm|xem thêm|nguồn|theo dõi|đăng ký|"
    r"(thạc sĩ|tiến sĩ|bác sĩ|phó giáo sư|giáo sư|chuyên gia|thầy thuốc)[^.]{0,60}$)",
    re.I,
)

# gặp những dòng này là hết nội dung bài (danh sách bài liên quan, bình luận…)
CUT_MARK_RE = re.compile(
    r"^(xem thêm|tài liệu tham khảo|bình luận|có thể bạn quan tâm|tin liên quan|"
    r"đọc thêm|các bài viết khác|bài viết liên quan|chia sẻ bài viết|"
    r"mời bạn đọc|theo dõi vinmec|tải ứng dụng)",
    re.I,
)

_DIACRITICS = str.maketrans(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ",
    "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
    "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd",
)


def key_text(s: str) -> str:
    """Bỏ dấu, thường hoá, "-" thành " " — để so mẫu chủ đề trên cả slug lẫn tiêu đề."""
    s = s.lower().translate(_DIACRITICS)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def topic_of(text: str, strong: bool = False) -> str:
    k = key_text(text)
    if DENY_RE.search(k):
        return ""
    if (STRONG_VACCINE_RE if strong else VACCINE_RE).search(k):
        return "vaccine"
    if NUTRITION_RE.search(k):
        return "dinh-duong"
    return ""


# --- đọc HTML ------------------------------------------------------------
class ArticleParser(HTMLParser):
    """Lấy <h1> và text trong div có class chứa 'post-detail' hoặc 'detail-content'."""

    BODY_CLASSES = ("post-detail", "detail-content")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_h1 = False
        self._depth = 0            # độ sâu khi đã vào vùng thân bài
        self._body_on = False
        self._skip = 0             # đang trong script/style
        self.parts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "h1" and not self.title:
            self._in_h1 = True
        if tag in ("script", "style"):
            self._skip += 1
        if not self._body_on and any(c in cls for c in self.BODY_CLASSES):
            self._body_on = True
            self._depth = 1
            return
        if self._body_on:
            self._depth += 1
            if tag in ("p", "br", "li", "div", "h2", "h3"):
                self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_h1 = False
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        if self._body_on:
            self._depth -= 1
            if self._depth <= 0:
                self._body_on = False

    def handle_data(self, data):
        if self._in_h1:
            self.title += data
        if self._body_on and not self._skip:
            self.parts.append(data)

    @property
    def body(self):
        return "".join(self.parts)


def clean_text(s: str) -> str:
    s = htmllib.unescape(s).replace("\r", "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def clean_answer(text: str, title: str) -> str:
    """Bỏ khung trang: tiêu đề lặp lại, dòng "Cố vấn chuyên môn", mục lục, tên bác sĩ."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    # 1. bỏ tiêu đề lặp lại ở đầu bài
    norm = lambda s: re.sub(r"\W+", " ", s.lower()).strip()
    while lines and norm(lines[0]).rstrip("?") == norm(title).rstrip("?"):
        lines.pop(0)
    # 2. trang hỏi-đáp: câu hỏi đã nằm ở tiêu đề, chỉ lấy phần sau "Trả lời"
    joined = "\n".join(lines)
    m = re.search(r"^\s*trả lời\s*[:.]?\s*$", joined, re.I | re.M)
    if m:
        lines = [ln.strip() for ln in joined[m.end():].split("\n") if ln.strip()]
    # 3. cắt ở mốc hết bài (bài liên quan, bình luận, tài liệu tham khảo)
    for i, ln in enumerate(lines):
        if CUT_MARK_RE.match(ln):
            lines = lines[:i]
            break
    # 4. bỏ dòng rác và dòng quá ngắn không có kết câu (mục lục, tên người)
    keep = []
    for ln in lines:
        if JUNK_LINE_RE.match(ln):
            continue
        if len(ln) < 40 and not ln.endswith((".", "!", "?", ":")):
            continue
        keep.append(ln)
    return " ".join(keep)


def cut_answer(text: str) -> str:
    """Cắt ở ranh giới câu gần ANSWER_MAX nhất để không cụt giữa câu."""
    text = text.strip()
    if len(text) <= ANSWER_MAX:
        return text
    head = text[:ANSWER_MAX]
    pos = max(head.rfind(". "), head.rfind("! "), head.rfind("? "))
    return (head[: pos + 1] if pos > ANSWER_MAX * 0.5 else head).strip()


def make_question(title: str) -> str:
    q = clean_text(title)
    q = re.sub(r"\s*[|—-]\s*Vinmec.*$", "", q, flags=re.I)
    q = re.sub(r"^(bài viết|video|tin tức)\s*:\s*", "", q, flags=re.I)
    q = q.rstrip(" .:,")
    return q if q.endswith("?") else f"{q}?"


# --- mạng ----------------------------------------------------------------
def get(url: str, tries: int = 2) -> str:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.text
            last = RuntimeError(f"HTTP {r.status_code}")
        except Exception as e:                        # noqa: BLE001
            last = e
        time.sleep(1 + i)
    raise last


def sitemap_urls() -> list:
    idx = get(SITEMAP)
    return re.findall(r"https://www\.vinmec\.com/sitemap/posts-vi-\d+\.xml", idx)


def all_slugs(refresh: bool = False) -> list:
    sm_dir = ROOT / "data/sources/vinmec/sitemaps"
    sm_dir.mkdir(parents=True, exist_ok=True)
    urls = sitemap_urls()
    out = []
    for u in urls:
        f = sm_dir / Path(urlparse(u).path).name
        if refresh or not f.exists():
            f.write_text(get(u), encoding="utf-8")
            time.sleep(0.2)
        out += re.findall(r"<loc>([^<]+)</loc>", f.read_text(encoding="utf-8"))
    return sorted(set(out))


def pick_articles(urls: list, strong: bool = False) -> list:
    rows = []
    for u in urls:
        slug = urlparse(u).path.rstrip("/").split("/")[-1]
        topic = topic_of(slug, strong)
        if topic:
            rows.append({"slug": slug, "url": u, "topic": topic})
    return rows


# --- dựng QA -------------------------------------------------------------
def fetch_one(item: dict, no_fetch: bool) -> dict | None:
    f = CACHE / f"{item['slug']}.html"
    try:
        if no_fetch:
            if not f.exists():
                return None
            page = f.read_text(encoding="utf-8")
        else:
            CACHE.mkdir(parents=True, exist_ok=True)
            if f.exists():
                page = f.read_text(encoding="utf-8")
            else:
                page = get(item["url"])
                f.write_text(page, encoding="utf-8")
                time.sleep(0.15)
    except Exception:                                  # noqa: BLE001
        return None

    p = ArticleParser()
    try:
        p.feed(page)
    except Exception:                                  # noqa: BLE001
        return None
    if not p.title:                                    # vài trang chỉ có ld+json
        m = re.search(r'"headline"\s*:\s*"([^"]{10,200})"', page)
        if not m:
            return None
        p.title = m.group(1)
    q = make_question(p.title)
    # chủ đề phải khớp ở tiêu đề, không chỉ ở slug (slug hay dính từ rác: soi, kem)
    if topic_of(q, item.get("strong", False)) != item["topic"]:
        return None
    a = clean_answer(clean_text(p.body), q)
    if len(q) < 10 or len(a) < ANSWER_MIN:
        return None
    return {"source": "Vinmec", "question": q, "answer": cut_answer(a),
            "link": item["url"], "_topic": item["topic"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, help="chỉ xử lý N bài đầu (thử nhanh)")
    ap.add_argument("--strong", action="store_true",
                    help="chỉ lấy bài nói về chính việc tiêm chủng (bỏ bài về bệnh)")
    ap.add_argument("--purge-cache", action="store_true",
                    help="xoá HTML đã tải sau khi dựng xong (tiết kiệm đĩa)")
    ap.add_argument("--per-topic", type=int, default=900,
                    help="trần số bài tải cho mỗi chủ đề (mặc định 900)")
    ap.add_argument("--no-fetch", action="store_true", help="chỉ dùng HTML đã cache")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--index", default=str(INDEX))
    args = ap.parse_args()

    urls = all_slugs()
    picked = pick_articles(urls, args.strong)
    for x in picked:
        x["strong"] = args.strong
    print(f"sitemap: {len(urls)} bài | lọc theo chủ đề: {len(picked)} bài "
          f"({sum(1 for x in picked if x['topic'] == 'vaccine')} vaccine, "
          f"{sum(1 for x in picked if x['topic'] == 'dinh-duong')} dinh dưỡng)")
    if not args.limit:                     # giữ trần tải cho nhẹ đĩa
        per = {}
        bounded = []
        for x in picked:
            per[x["topic"]] = per.get(x["topic"], 0) + 1
            if per[x["topic"]] <= args.per_topic:
                bounded.append(x)
        picked = bounded
        print(f"  giới hạn {args.per_topic}/chủ đề → {len(picked)} bài")
    if args.limit:
        picked = picked[: args.limit]

    ok, seen = [], set()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, row in enumerate(ex.map(lambda x: fetch_one(x, args.no_fetch), picked), 1):
            if row:
                key = re.sub(r"\W+", " ", row["question"].lower()).strip()
                if key not in seen:
                    seen.add(key)
                    ok.append(row)
            if i % 200 == 0:
                print(f"  {i}/{len(picked)} bài, {len(ok)} dòng dùng được, "
                      f"{time.time() - t0:.0f}s", flush=True)

    topics = {}
    for r in ok:
        topics[r["_topic"]] = topics.get(r["_topic"], 0) + 1
    Path(args.index).parent.mkdir(parents=True, exist_ok=True)
    with open(args.index, "w", encoding="utf-8") as f:
        for r in ok:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    out = Path(args.out)
    with out.open("w", encoding="utf-8") as f:
        for r in ok:
            f.write(json.dumps({k: v for k, v in r.items() if k != "_topic"},
                               ensure_ascii=False) + "\n")

    if args.purge_cache:
        import shutil
        shutil.rmtree(CACHE, ignore_errors=True)
        print(f"đã xoá cache HTML: {CACHE.relative_to(ROOT)}")

    shown = out.relative_to(ROOT) if out.is_absolute() else out
    print(f"\n{len(ok)} dòng → {shown}  ({topics})")
    print("Bước tiếp: .venv/bin/python scripts/validate_data.py "
          f"{shown}")


if __name__ == "__main__":
    main()
