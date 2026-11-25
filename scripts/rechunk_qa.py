"""P2: tách đáp án KB dài thành các đoạn theo mục (nguyên nhân / triệu chứng / xử trí...).

Chỉ ĐỌC data/processed/kb.jsonl và GHI ra data/processed/kb_chunked.jsonl.
Chưa nạp lại ChromaDB — cần duyệt chất lượng chunk trước.

Chạy:
  .venv/bin/python scripts/rechunk_qa.py --preview 6      # xem mẫu
  .venv/bin/python scripts/rechunk_qa.py                  # xuất toàn bộ
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "data/processed/kb.jsonl"
OUT = ROOT / "data/processed/kb_chunked.jsonl"

LONG_ANSWER = 800      # chỉ tách đáp án dài hơn ngần này
MAX_CHUNK = 900        # ký tự/chunk, dưới giới hạn ~1600 ký tự (512 token) của e5
MIN_CHUNK = 120        # chunk ngắn hơn thì gộp vào chunk trước

# Tiêu đề mục thường gặp trong câu trả lời y khoa tiếng Việt
SECTION_RE = re.compile(
    r"^\s*(?:[-•*]\s*)?"
    r"(nguyên nhân|nguyên do|do đâu|triệu chứng|dấu hiệu|biểu hiện|"
    r"chẩn đoán|xét nghiệm|điều trị|cách điều trị|hướng điều trị|"
    r"cách xử trí|xử trí|sơ cứu|cách chăm sóc|chăm sóc|"
    r"phòng ngừa|phòng bệnh|cách phòng|biến chứng|"
    r"khi nào (?:cần|nên) (?:đi khám|gặp bác sĩ|nhập viện)|"
    r"chế độ (?:ăn|dinh dưỡng|sinh hoạt)|dinh dưỡng|lưu ý|kết luận)"
    r"\s*[:\-–]?\s*",
    re.IGNORECASE,
)
SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+")


def split_sections(answer: str):
    """Cắt đáp án thành [(tiêu đề, nội dung)] theo tiêu đề mục; không có mục -> [("", answer)]."""
    lines = [ln.strip() for ln in answer.splitlines() if ln.strip()]
    blocks, cur_title, cur = [], "", []
    for ln in lines:
        # chỉ coi là tiêu đề mục khi dòng ngắn, tránh bắt nhầm câu văn dài
        m = SECTION_RE.match(ln) if len(ln) <= 90 else None
        if m:
            if cur:
                blocks.append((cur_title, " ".join(cur)))
            cur_title, cur = ln[:60], [ln]
        else:
            cur.append(ln)
    if cur:
        blocks.append((cur_title, " ".join(cur)))
    return blocks or [("", answer)]


def pack(blocks, head: str):
    """Gộp/tách block thành chunk <= MAX_CHUNK, giữ tiêu đề mục làm nhãn."""
    out = []
    for title, body in blocks:
        body = body.strip()
        if not body:
            continue
        while len(body) > MAX_CHUNK:
            cut = body.rfind(". ", 0, MAX_CHUNK)
            cut = cut + 1 if cut > MAX_CHUNK * 0.5 else MAX_CHUNK
            out.append((title, body[:cut].strip()))
            body = body[cut:].strip()
        out.append((title, body))

    # gộp chunk quá ngắn vào chunk trước, bỏ mảnh vụn
    merged = []
    for title, body in out:
        body = body.strip()
        if not body:
            continue
        if merged and len(body) < MIN_CHUNK and len(merged[-1][1]) + len(body) <= MAX_CHUNK:
            merged[-1] = (merged[-1][0], merged[-1][1] + " " + body)
        elif len(body) < 40 and merged:
            merged[-1] = (merged[-1][0], merged[-1][1] + " " + body)
        else:
            merged.append((title, body))
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=int, default=0, help="số mẫu in ra")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--kb", default=str(KB), help="file KB đầu vào (mặc định kb.jsonl)")
    ap.add_argument("--out", default=str(OUT), help="file chunk đầu ra")
    args = ap.parse_args()

    kb_path = Path(args.kb) if Path(args.kb).is_absolute() else ROOT / args.kb
    out_path = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    rows = [json.loads(l) for l in kb_path.open(encoding="utf-8") if l.strip()]
    if args.limit:
        rows = rows[: args.limit]

    out_rows, stats = [], Counter()
    for i, r in enumerate(rows):
        ans = r["answer"].strip()
        if len(ans) <= LONG_ANSWER:
            chunks = [( "", ans)]
            stats["giữ nguyên"] += 1
        else:
            blocks = split_sections(ans)
            chunks = pack(blocks, r["question"])
            if len(chunks) == 1:
                stats["dài nhưng không có tiêu đề mục"] += 1
            else:
                stats["đã tách"] += 1
        for sec, text in chunks:
            out_rows.append({
                "parent_id": i,
                "source": r["source"],
                "link": r.get("link", ""),
                "question": r["question"],
                "section": sec,
                "text": text,
            })

    lens = [len(x["text"]) for x in out_rows]
    over = sum(1 for v in lens if v > 1600)
    print(f"Đầu vào {len(rows)} dòng -> {len(out_rows)} chunk")
    for k, v in stats.most_common():
        print(f"  {k:<28}{v:>6}")
    print(f"  độ dài chunk: min {min(lens)}, trung bình {sum(lens) // len(lens)}, max {max(lens)}")
    print(f"  chunk vượt ~512 token của e5: {over} ({100 * over / len(lens):.1f}%)")

    if args.preview:
        print("\n== Mẫu ==")
        shown = 0
        for x in out_rows:
            if len(x["text"]) < 400 and len(x["question"]) < 200:
                continue
            print(f"\n[{x['section'] or '(không có mục)'}] q={x['question'][:90]}")
            print(f"  -> {x['text'][:300]}...")
            shown += 1
            if shown >= args.preview:
                break

    if not args.preview or args.preview and args.limit:
        with out_path.open("w", encoding="utf-8") as f:
            for x in out_rows:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
        print(f"\nĐã ghi {out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path}")
    else:
        print("\n(chế độ preview: chưa ghi file; bỏ --preview để xuất)")


if __name__ == "__main__":
    main()
