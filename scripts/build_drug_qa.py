"""Sinh QA 5 khía cạnh cho từng hoạt chất từ chuyên luận Dược thư (mirror Bạch Mai).

Bóc các mục Chỉ định / Chống chỉ định / Thận trọng / Tác dụng không mong muốn /
Tương tác thuốc rồi xuất JSONL đúng schema kb.jsonl.

Hai nguồn đầu vào:
  - mặc định: `data/processed/kb_drugs_25.jsonl` (25 hoạt chất) → `kb_drugs_25_full.jsonl`
  - `--index data/sources/duocthu/index.jsonl`: danh mục do `build_drug_index.py` sinh ra,
    đọc HTML từ cache `data/sources/duocthu/raw/` → `kb_drugs_full.jsonl`

Chạy:
    .venv/bin/python scripts/build_drug_qa.py
    .venv/bin/python scripts/build_drug_qa.py --index data/sources/duocthu/index.jsonl
"""

import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/processed/kb_drugs_25.jsonl"
OUT = ROOT / "data/processed/kb_drugs_25_full.jsonl"

SOURCE = "DuocThu-BachMai"
RAW_DIR = ROOT / "data/sources/duocthu/raw"

MAX_ANSWER = 350
SAFETY = " Chỉ dùng theo chỉ định của bác sĩ."

# Đủ để nhận ra điểm kết thúc của một mục, kể cả trang không in đậm tiêu đề.
# Chỉ khớp tiêu đề cấp mục; các tiêu đề con trong ADR ("Thường gặp, ADR > 1/100")
# cố ý không khớp để nội dung của chúng vẫn nằm trong mục.
HEADING_RE = re.compile(
    r"^(chỉ định|chống chỉ định|thận trọng|tương tác thuốc|tác dụng không mong muốn"
    r"|liều lượng|dạng thuốc|dược lý|thời kỳ|bảo quản|quá liều|đặc tính"
    r"|tên chung quốc tế|mã atc|loại thuốc|chú ý|ghi chú|chế phẩm|đóng gói"
    r"|tương kỵ|hướng dẫn cách xử trí adr|[đð]ộ ổn định và bảo quản)\b",
    re.I,
)

FACETS = [
    ("indication", r"^chỉ định$", "{name} được chỉ định trong: ",
     "{name} được chỉ định trong những trường hợp nào?"),
    ("contraindication", r"^chống chỉ định$", "{name} chống chỉ định ở: ",
     "Ai không nên dùng {name}?"),
    ("caution", r"^thận trọng$", "Khi dùng {name} cần thận trọng: ",
     "Cần thận trọng khi dùng {name} ở những ai?"),
    ("adr", r"^tác dụng không mong muốn", "Tác dụng không mong muốn của {name}: ",
     "Tác dụng phụ thường gặp của {name} là gì?"),
    ("interaction", r"^tương tác thuốc$", "{name} tương tác với: ",
     "{name} tương tác với những thuốc nào?"),
]

DOSE_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|gam|kg|ml|viên|ống|giọt|mEq|mmol|UI|đơn vị)\b"
    r"|\d+\s*lần\s*(?:/|mỗi)?\s*ngày",
    re.I,
)
SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+")


class Paragraphs(HTMLParser):
    """Bóc các đoạn <p> kèm cờ in đậm; đủ dùng cho trang chuyên luận."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paras: list[tuple[str, bool]] = []
        self._cur: dict | None = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "p":
            self._flush()
            self._cur = {"text": [], "bold": False}
        elif tag in ("b", "strong") and self._cur is not None:
            self._cur["bold"] = True
        elif tag == "br" and self._cur is not None:
            self._cur["text"].append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag == "p":
            self._flush()

    def handle_data(self, data):
        if not self._skip and self._cur is not None:
            self._cur["text"].append(data)

    def _flush(self):
        if self._cur is None:
            return
        text = " ".join("".join(self._cur["text"]).split())
        if text:
            self.paras.append((text, self._cur["bold"]))
        self._cur = None


def is_heading(text: str, _bold: bool = False) -> bool:
    if len(text) >= 100 or text.rstrip().endswith((".", ";")):
        return False
    return bool(HEADING_RE.match(text))


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; medical-kb-builder)"})
    last = None
    for _ in range(2):
        try:
            with urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001 - báo lỗi rồi bỏ qua trang
            last = exc
    raise last  # type: ignore[misc]


def fetch_page(url: str) -> str:
    """Đọc HTML từ cache của `scripts/build_drug_index.py` trước, chỉ ra mạng khi cần."""
    slug = urlparse(url).path.strip("/").split("/")[-1]
    cached = RAW_DIR / f"{slug}.html"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    return fetch(url)


def sections(paras: list[tuple[str, bool]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i, (text, bold) in enumerate(paras):
        if not is_heading(text, bold):
            continue
        for key, pattern, _prefix, _q in FACETS:
            if key in out or not re.match(pattern, text, re.I):
                continue
            body = []
            for nxt, nxt_bold in paras[i + 1:]:
                if is_heading(nxt, nxt_bold):
                    break
                body.append(nxt)
            if body:
                out[key] = " ".join(body)
            break
    return out


def usable(text: str) -> str:
    """Bỏ câu có số liều/tần suất; gộp lại thành một đoạn."""
    keep = [s for s in SENTENCE_RE.split(text) if s.strip() and not DOSE_RE.search(s)]
    return " ".join(keep).strip()


def trim(text: str, budget: int) -> str:
    if len(text) <= budget:
        return text
    cut = text[:budget]
    edge = max(cut.rfind(". "), cut.rfind("; "))
    if edge >= budget * 0.5:
        return cut[: edge + 1].strip()
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut).rstrip(" ,;:") + "…"


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def load_source(args) -> list[dict]:
    """Trả về list {name, source, link}; hoặc đọc danh mục do build_drug_index.py sinh ra."""
    if args.index:
        path = Path(args.index) if Path(args.index).is_absolute() else ROOT / args.index
        idx = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
        keep = [r for r in idx if len(r.get("facets") or []) >= args.min_facets]
        print(f"Đọc {len(idx)} chuyên luận trong danh mục, dùng {len(keep)} "
              f"(đủ ≥{args.min_facets} khía cạnh)")
        return [{"name": r["name"], "source": SOURCE, "link": r["url"]} for r in keep]

    rows = [json.loads(line) for line in SRC.open(encoding="utf-8") if line.strip()]
    print(f"Đọc {len(rows)} hoạt chất từ {SRC.relative_to(ROOT)}")
    for r in rows:
        name = r["question"].split(" thuộc nhóm")[0].strip()
        r["name"] = name[:1].upper() + name[1:]
    return rows


def main():
    ap = argparse.ArgumentParser(description="Sinh QA 5 khía cạnh từ chuyên luận Dược thư")
    ap.add_argument("--index", help="danh mục data/sources/duocthu/index.jsonl (mở rộng toàn bộ)")
    ap.add_argument("--min-facets", type=int, default=5,
                    help="số khía cạnh tối thiểu của chuyên luận khi dùng --index (mặc định 5)")
    ap.add_argument("--out", help="file JSONL đầu ra (mặc định theo nguồn đang đọc)")
    ap.add_argument("--min-answer", type=int, default=100,
                    help="bỏ đáp án ngắn hơn N ký tự (khớp luật R3 trong DATA_CONTRACT.md)")
    ap.add_argument("--partial", action="store_true",
                    help="giữ cả hoạt chất thiếu khía cạnh (mặc định bỏ cả hoạt chất)")
    args = ap.parse_args()

    rows = load_source(args)
    out_path = Path(args.out) if args.out else (
        ROOT / "data/processed/kb_drugs_full.jsonl" if args.index else OUT)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    def work(row):
        name = unescape(row["name"]).strip()   # tên gốc có entity escape 2 lần
        try:
            html = fetch_page(row["link"])
        except Exception as exc:  # noqa: BLE001
            return name, {}, f"tải lỗi: {type(exc).__name__}"
        secs = sections(_parse(html))
        return name, secs, "" if secs else "không thấy mục nào"

    out, missing = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(work, rows))

    # Không trả lời được gì: bỏ, đừng đếm là "có dữ liệu"
    empty_re = re.compile(r"^(chưa|không|chưa được) (có )?(thông tin|biết|rõ)", re.I)

    for row, (name, secs, err) in zip(rows, results):
        if err:
            missing.append((name, err))
            continue
        got, dropped = {}, []
        for key, _pattern, prefix, question in FACETS:
            body = secs.get(key)
            if not body:
                dropped.append(key)
                continue
            prefix = prefix.format(name=name)
            body = lower_first(usable(body))
            if not body:
                dropped.append(key + " (toàn câu có số liều)")
                continue
            if empty_re.match(body):
                dropped.append(key + " (trả lời rỗng)")
                continue
            budget = MAX_ANSWER - len(prefix) - len(SAFETY)
            if budget < 80:
                dropped.append(key + " (tên quá dài)")
                continue
            answer = prefix + trim(body, budget) + SAFETY
            if len(answer) < args.min_answer:
                dropped.append(key + f" (đáp án {len(answer)} ký tự)")
                continue
            got[key] = {
                "source": row["source"],
                "question": question.format(name=name),
                "answer": answer,
                "link": row["link"],
                "facet": key,
            }

        if dropped and not args.partial:
            # Luật R9: một hoạt chất phải đủ 5 khía cạnh, thiếu thì bỏ cả hoạt chất
            for reason in dropped:
                missing.append((name, reason))
            continue
        out += [got[k] for k, _p, _pre, _q in FACETS if k in got]

    # Khử trùng câu hỏi với KB/eval hiện có và trong chính file mới
    existing = set()
    for path in ("data/processed/kb.jsonl", "data/processed/eval.jsonl"):
        p = ROOT / path
        if p.exists():
            existing |= {json.loads(l)["question"].strip().lower() for l in p.open(encoding="utf-8")}
    seen, kept = set(), []
    for r in out:
        key = r["question"].strip().lower()
        if key in existing or key in seen:
            missing.append((r["question"], "trùng câu hỏi"))
            continue
        seen.add(key)
        kept.append(r)

    with out_path.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Đã ghi {len(kept)} QA vào {out_path.relative_to(ROOT)}")
    print(f"Thiếu/không dùng được: {len(missing)}")
    why = Counter(reason for _name, reason in missing)
    for reason, n in why.most_common(6):
        print(f"  {n:>5}  {reason[:70]}")
    if len(missing) <= 20:
        for name, reason in missing:
            print(f"  - {name}: {reason}")
    lens = [len(r["answer"]) for r in kept]
    if lens:
        print(f"Độ dài đáp án: min {min(lens)}, max {max(lens)} (giới hạn {MAX_ANSWER})")
    drugs = {r["link"].rstrip("/").split("/")[-1] for r in kept}
    print(f"Hoạt chất có ít nhất 1 dòng: {len(drugs)}")
    if any(v > MAX_ANSWER for v in lens):
        sys.exit("Có đáp án vượt giới hạn")


def _parse(html: str) -> list[tuple[str, bool]]:
    parser = Paragraphs()
    parser.feed(html)
    parser.close()
    # Nguồn có entity bị escape 2 lần ("&amp;#8211;") nên HTMLParser chỉ trả về
    # chuỗi "&#8211;" nguyên văn; giải mã lần nữa để KB không chứa entity.
    return [(unescape(text), bold) for text, bold in parser.paras]


if __name__ == "__main__":
    main()
