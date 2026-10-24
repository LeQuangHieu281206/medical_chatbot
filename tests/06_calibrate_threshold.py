import json
import random
from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

DB_PATH = "app/db/chroma_db"
COLLECTION = "medical_kb"
MODEL_NAME = "intfloat/multilingual-e5-small"
EVAL_PATH = Path("data/processed/eval.jsonl")
N_EVAL = 500

SHORT_MED = [
    "đau đầu", "ho kéo dài phải làm sao", "thuốc hạ sốt cho trẻ em",
    "huyết áp cao nên ăn gì", "tiểu đường là gì", "đau bụng bên phải",
    "mất ngủ lâu ngày", "triệu chứng viêm họng", "cách chăm sóc vết thương",
    "uống thuốc kháng sinh bao lâu", "phụ nữ mang thai nên khám mấy lần",
    "nổi mề đay do đâu", "đau lưng cấp", "bị chóng mặt hoa mắt",
    "vaccine covid có tác dụng phụ gì",
]

OFF_TOPIC = [
    "Công thức nấu phở bò", "Giá bitcoin hôm nay bao nhiêu?",
    "Thời tiết Hà Nội ngày mai thế nào?", "Viết cho tôi một đoạn code Python đảo ngược chuỗi",
    "Đội tuyển Việt Nam đá trận nào gần nhất?", "Cách làm bánh flan mềm mịn",
    "Giá vàng SJC hôm nay", "Kể một câu chuyện cười",
    "Nên đi du lịch Đà Nẵng vào tháng mấy?", "Giải phương trình x^2 - 5x + 6 = 0",
    "Cách tăng điểm IELTS speaking", "Mua laptop nào tốt dưới 20 triệu",
    "Lãi suất ngân hàng hiện nay là bao nhiêu?", "Tóm tắt truyện Kiều",
    "Cách cài đặt Windows 11", "Thủ đô của Pháp là gì?",
    "Giá vé máy bay đi Phú Quốc", "Bộ phim nào hay nhất năm nay?",
    "Cách chọn xe máy cho sinh viên", "Làm thế nào để viết CV xin việc?",
    "Hôm nay có trận bóng đá nào?", "Dạy tôi chơi guitar cơ bản",
    "Cách đầu tư chứng khoán cho người mới", "Lập trình web học bắt đầu từ đâu?",
    "Xin chào bạn là ai?", "Bạn có thể làm gì?",
]

BORDERLINE = [
    "Phở bò có bao nhiêu calo?", "Cách tập gym để tăng cơ nhanh",
    "Nên ăn gì để giảm cân?", "Nhà thuốc nào gần đây còn mở cửa?",
    "Cách chạy bộ cho người mới bắt đầu", "Uống cà phê có tốt không?",
    "Làm sao để ngủ ngon hơn?", "Chế độ ăn keto là gì?",
]

model = SentenceTransformer(MODEL_NAME)
col = chromadb.PersistentClient(path=DB_PATH).get_collection(COLLECTION)


def top1(queries):
    embs = model.encode(
        [f"query: {q}" for q in queries], normalize_embeddings=True, batch_size=32
    ).tolist()
    res = col.query(query_embeddings=embs, n_results=1)
    return [d[0] for d in res["distances"]]


with open(EVAL_PATH, encoding="utf-8") as f:
    eval_rows = [json.loads(line) for line in f]
random.Random(7).shuffle(eval_rows)
eval_qs = [r["question"] for r in eval_rows[:N_EVAL]]

d_eval = np.array(top1(eval_qs))
d_short = np.array(top1(SHORT_MED))
d_off = np.array(top1(OFF_TOPIC))
d_border = np.array(top1(BORDERLINE))

print("\n=== Phân bố khoảng cách top-1 của câu y tế (eval, %d câu) ===" % len(d_eval))
for p in (50, 90, 95, 99):
    print(f"p{p}: {np.percentile(d_eval, p):.3f}")
print(f"max: {d_eval.max():.3f}")


def show(name, queries, dists):
    print(f"\n=== {name} ===")
    for q, d in sorted(zip(queries, dists), key=lambda x: x[1]):
        print(f"  {d:.3f} | {q}")


show("Câu y tế ngắn", SHORT_MED, d_short)
show("Câu ngoài chủ đề", OFF_TOPIC, d_off)
show("Câu ranh giới", BORDERLINE, d_border)

print("\n=== Thử các ngưỡng (khoảng cách <= ngưỡng thì cho qua) ===")
print("ngưỡng | eval cho qua | y tế ngắn cho qua | ngoài chủ đề bị chặn")
for t in (0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16):
    print(
        f" {t:.2f}  |   {np.mean(d_eval <= t) * 100:5.1f}%     |"
        f"      {np.mean(d_short <= t) * 100:5.1f}%       |"
        f"      {np.mean(d_off > t) * 100:5.1f}%"
    )