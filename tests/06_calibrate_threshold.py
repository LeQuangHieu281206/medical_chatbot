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

# ============================================================
# TẠO VÀ LƯU ẢNH TRỰC QUAN HÓA CHO BÁO CÁO & COLAB
# ============================================================
try:
    import os
    import matplotlib.pyplot as plt

    os.makedirs("charts_output", exist_ok=True)
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    # Biểu đồ 1: Boxplot phân bố thực nghiệm & 3 phân vùng
    data = [d_eval, d_short, d_border, d_off]
    labels = [f'Y tế chuẩn\n({len(d_eval)} câu)', f'Y tế ngắn\n({len(d_short)} câu)', 
              f'Ranh giới\n({len(d_border)} câu)', f'Ngoài chủ đề\n({len(d_off)} câu)']
    colors = ['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728']

    ax1.axhspan(0.04, 0.12, color='#e8f5e9', alpha=0.8, label='Pass Zone (d <= 0.12)')
    ax1.axhspan(0.12, 0.14, color='#fff9c4', alpha=0.8, label='Grey Zone (0.12 < d <= 0.14)')
    ax1.axhspan(0.14, 0.25, color='#ffebee', alpha=0.8, label='Reject Zone (d > 0.14)')

    box = ax1.boxplot(data, patch_artist=True, labels=labels, widths=0.45,
                      medianprops=dict(color='black', linewidth=1.8))
    for patch, c in zip(box['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)

    ax1.axhline(0.12, color='green', linestyle='--', linewidth=1.8, label='PASS_MAX = 0.12')
    ax1.axhline(0.14, color='red', linestyle='--', linewidth=1.8, label='REJECT_MIN = 0.14')
    ax1.set_title('Phân bố khoảng cách Top-1 Cosine thực nghiệm', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Khoảng cách Cosine (d)', fontsize=10, fontweight='bold')
    ax1.set_ylim(0.03, 0.25)
    ax1.legend(loc='upper left', fontsize=8.5, frameon=True, facecolor='white')
    ax1.grid(axis='y', linestyle=':', alpha=0.6)

    # Biểu đồ 2: Đường cong cân bằng tỷ lệ lọc
    thresholds = [0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16]
    pass_rates = [np.mean(d_eval <= t) * 100 for t in thresholds]
    reject_rates = [np.mean(d_off > t) * 100 for t in thresholds]

    ax2.plot(thresholds, pass_rates, marker='s', color='#2ca02c', linewidth=2.5, markersize=7, label='Độ phủ y tế (Eval %)')
    ax2.plot(thresholds, reject_rates, marker='o', color='#d62728', linewidth=2.5, markersize=7, label='Chặn ngoài chủ đề (An toàn %)')
    ax2.scatter([0.12], [pass_rates[2]], color='green', s=120, zorder=5)
    ax2.annotate(f'PASS_MAX=0.12\n(Phủ {pass_rates[2]:.1f}%, Chặn 100%)', 
                 xy=(0.12, pass_rates[2]), xytext=(0.102, 85),
                 arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.2),
                 fontsize=9, fontweight='bold', backgroundcolor='white')

    ax2.set_title('Đường cong cân bằng theo ngưỡng lọc Cosine', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Ngưỡng khoảng cách (t)', fontsize=10, fontweight='bold')
    ax2.set_ylabel('Tỷ lệ phần trăm (%)', fontsize=10, fontweight='bold')
    ax2.set_ylim(50, 105)
    ax2.set_xticks(thresholds)
    ax2.legend(loc='lower left', fontsize=9.5, frameon=True, facecolor='white')
    ax2.grid(True, linestyle=':', alpha=0.6)

    out_fig = "charts_output/danh_gia_06_nguong_loc.png"
    plt.tight_layout()
    plt.savefig(out_fig, dpi=300)
    plt.close()
    print(f"\n[XONG] Đã tạo ảnh kết quả: {out_fig}")
except ImportError:
    print("\n[CHÚ Ý] Cần matplotlib để tạo ảnh đồ thị: pip install matplotlib")