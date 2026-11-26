"""Đo khả năng truy xuất tài liệu ĐÚNG BỆNH cho các câu đã biết là sai.

Không cần LLM, không cần chấm điểm: chỉ hỏi ChromaDB và kiểm tra xem tài liệu
chứa từ khoá bệnh đúng có nằm trong ngữ cảnh mà pipeline đưa cho model không.
Nhờ vậy sửa truy xuất mà không phải chạy lại 40 phút sinh câu trả lời.

Cách chạy::

    .venv/bin/python tests/56_doc_recall.py            # bảng hiện trạng
    .venv/bin/python tests/56_doc_recall.py --top 50   # xem tài liệu đúng ở hạng nào

Cột ý nghĩa:
    hang  : hạng của tài liệu đúng trong 50 tài liệu gần nhất (1 = gần nhất)
    trong : tài liệu đó CÓ được đưa vào ngữ cảnh của pipeline không (Y/N)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

SRC = ROOT / "data" / "sources"
EVAL = SRC / "eval_answers_50.jsonl"

from _recall_patterns import PATTERNS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=str(EVAL))
    ap.add_argument("--top", type=int, default=50, help="số tài liệu gần nhất để dò")
    args = ap.parse_args()

    from app.services.pipeline import MedicalChatbot

    ev = {json.loads(l)["id"]: json.loads(l)
          for l in open(args.eval, encoding="utf-8") if l.strip()}
    bot = MedicalChatbot()

    n_ctx = n_rank = 0
    print(f"{'id':<5}{'hạng':>6}{'trong':>7}  tài liệu đúng")
    print("-" * 78)
    for qid, pat in PATTERNS.items():
        if qid not in ev:
            continue
        q = ev[qid]["question"]
        ctx = bot.retrieve(q, [], True)
        # so khớp bằng NỘI DUNG (tiêu đề trong ngữ cảnh có thể bị thêm tiền tố
        # "keyword - "), chuẩn hoá khoảng trắng và cắt 60 ký tự
        ctx_texts = {re.sub(r"\s+", " ", d.get("text", "")).lower()[:60] for d in ctx}
        emb = bot.embedder.encode([f"query: {q}"], normalize_embeddings=True).tolist()

        rank, title, matched = 0, "", ""
        for col in (bot.encyc, bot.collection):
            if col is None:
                continue
            r = col.query(query_embeddings=emb, n_results=args.top,
                          include=["documents", "metadatas", "distances"])
            for i, (doc, meta) in enumerate(zip(r["documents"][0], r["metadatas"][0]), 1):
                if doc and re.search(pat, doc, re.I):
                    if not rank or i < rank:
                        rank = i
                        title = (meta or {}).get("question", doc[:60])[:58]
                        matched = re.sub(r"\s+", " ", doc).lower()[:60]
                    break
        # tài liệu vào ngữ cảnh thì phần đầu nội dung trùng với ctx_texts
        inside = "Y" if any(matched[:45] in t or t[:45] in matched for t in ctx_texts) else "N"
        n_rank += 1 if rank else 0
        n_ctx += 1 if inside == "Y" else 0
        print(f"{qid:<5}{rank if rank else '-':>6}{inside:>7}  {title}")

    print("-" * 78)
    print(f"có bài đúng trong {args.top} tài liệu gần nhất: {n_rank}/{len(PATTERNS)}")
    print(f"bài đúng CÓ mặt trong ngữ cảnh pipeline : {n_ctx}/{len(PATTERNS)}")
    print("\nNếu 'bài đúng có trong kho nhưng không vào ngữ cảnh' -> sửa quota/bể ứng viên.")
    print("Nếu 'không có bài đúng trong kho' -> phải bổ sung dữ liệu, rerank không cứu được.")


if __name__ == "__main__":
    main()
