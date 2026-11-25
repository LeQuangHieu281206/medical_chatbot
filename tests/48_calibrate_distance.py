"""Đo phân bố khoảng cách của tài liệu gần nhất để chọn ngưỡng loại tài liệu rác.

Với mỗi câu hỏi: lấy top-1 của cả hai collection (bài viết y khoa + hỏi đáp) rồi
lấy khoảng cách nhỏ hơn. Câu hỏi y tế thật lấy từ bộ eval 400 dòng (trường
"clean"); câu ngoài chủ đề lấy từ danh sách của tests/06.

Chạy: .venv/bin/python tests/48_calibrate_distance.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import chromadb  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.services.topic_filter import DB_PATH, COLLECTION, EMBED_MODEL  # noqa: E402

SRC = ROOT / "data/sources/eval_chuan_hoa_cau_hoi_y_te.jsonl"

OFF_TOPIC = [
    "Công thức nấu phở bò", "Giá bitcoin hôm nay bao nhiêu?",
    "Thời tiết Hà Nội ngày mai thế nào?",
    "Viết cho tôi một đoạn code Python đảo ngược chuỗi",
    "Đội tuyển Việt Nam đá trận nào gần nhất?", "Cách làm bánh flan mềm mịn",
    "Giá vàng SJC hôm nay", "Kể một câu chuyện cười",
    "Nên đi du lịch Đà Nẵng vào tháng mấy?",
    "Giải phương trình x^2 - 5x + 6 = 0", "Cách tăng điểm IELTS speaking",
    "Mua laptop nào tốt dưới 20 triệu",
    "Lãi suất ngân hàng hiện nay là bao nhiêu?", "Tóm tắt truyện Kiều",
    "Cách cài đặt Windows 11", "Thủ đô của Pháp là gì?",
    "Giá vé máy bay đi Phú Quốc", "Bộ phim nào hay nhất năm nay?",
    "Cách chọn xe máy cho sinh viên", "Làm thế nào để viết CV xin việc?",
    "Hôm nay có trận bóng đá nào?", "Dạy tôi chơi guitar cơ bản",
    "Cách đầu tư chứng khoán cho người mới",
    "Lập trình web học bắt đầu từ đâu?", "Xin chào bạn là ai?",
    "Bạn có thể làm gì?",
]

VAGUE = ["tôi bị ốm", "tôi thấy mệt", "người tôi khó chịu", "tôi không khoẻ"]


def top1(model, cols, texts, batch=48):
    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        emb = model.encode([f"query: {t}" for t in chunk],
                           normalize_embeddings=True).tolist()
        for j, e in enumerate(emb):
            out.append(min(c.query(query_embeddings=[e], n_results=1)
                           ["distances"][0][0] for c in cols))
        print(f"  ...{min(i + batch, len(texts))}/{len(texts)}", end="\r")
    print(" " * 30, end="\r")
    return np.array(out)


def show(name, d):
    q = np.percentile(d, [50, 90, 95, 99])
    print(f"{name:22s} n={len(d):4d}  min={d.min():.4f}  p50={q[0]:.4f}  "
          f"p90={q[1]:.4f}  p95={q[2]:.4f}  p99={q[3]:.4f}  max={d.max():.4f}")


def main():
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    questions = [r["clean"] for r in rows if r.get("loai", "sach") != "sach"]

    client = chromadb.PersistentClient(path=DB_PATH)
    cols = [client.get_collection(COLLECTION),
            client.get_collection(f"{COLLECTION}_vimedaqa")]
    model = SentenceTransformer(EMBED_MODEL)

    print(f"{len(questions)} câu y tế (bộ eval 400) + {len(OFF_TOPIC)} câu ngoài "
          f"chủ đề + {len(VAGUE)} câu mơ hồ\n")
    d_in = top1(model, cols, questions)
    d_off = top1(model, cols, OFF_TOPIC)
    d_vague = top1(model, cols, VAGUE)

    show("Câu y tế thật", d_in)
    show("Câu mơ hồ", d_vague)
    show("Câu ngoài chủ đề", d_off)

    for thr in (0.10, 0.11, 0.12, 0.13, 0.14):
        keep = (d_in <= thr).mean() * 100
        drop = (d_off > thr).mean() * 100
        print(f"  ngưỡng {thr:.2f}: giữ được {keep:5.1f}% câu y tế, "
              f"loại được {drop:5.1f}% câu ngoài chủ đề")


if __name__ == "__main__":
    main()
