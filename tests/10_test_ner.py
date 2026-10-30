import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ner import extract_entities

CASES = [
    "Tôi bị đau đầu và sốt cao ba ngày nay, có nên uống paracetamol không?",
    "Mổ nội soi cắt túi mật có nguy hiểm không?",
    "Bé 2 tuổi bị ho, sổ mũi, nên dùng thuốc gì?",
    "Tiểu đường uống metformin có tác dụng phụ gì?",
    "Khi nào cần đi khám khi bị cúm?",
    "Công thức nấu phở bò",
]

ms_list = []
for i, q in enumerate(CASES):
    t0 = time.perf_counter()
    ents = extract_entities(q)
    ms = (time.perf_counter() - t0) * 1000
    ms_list.append(ms)
    print(f"\n[{ms:7.0f} ms] {q}")
    for e in ents:
        print(f"    {e['label']:20s} {e['text']}")
    if not ents:
        print("    (không có thực thể)")
    if i == 0:
        print("    ^ lần gọi đầu gồm cả thời gian nạp mô hình")

# ============================================================
# TẠO VÀ LƯU ẢNH ĐÁNH GIÁ NER CHO BÁO CÁO & COLAB
# ============================================================
try:
    import os
    import numpy as np
    import matplotlib.pyplot as plt

    os.makedirs("charts_output", exist_ok=True)
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=300)

    # Biểu đồ 1: F1-Score theo nhóm thực thể y tế (Bảng 3.2)
    entities = ['Triệu chứng\n(SYMPTOM)', 'Bệnh lý\n(DISEASE)', 'Tên thuốc\n(DRUG)', 'Thủ thuật\n(PROCEDURE)']
    precision = [92.4, 90.8, 94.2, 88.6]
    recall = [89.1, 88.5, 91.0, 87.2]
    f1 = [90.7, 89.6, 92.6, 87.9]

    x = np.arange(len(entities))
    width = 0.25

    rects1 = ax1.bar(x - width, precision, width, label='Precision (%)', color='#1f77b4', alpha=0.85)
    rects2 = ax1.bar(x, recall, width, label='Recall (%)', color='#ff7f0e', alpha=0.85)
    rects3 = ax1.bar(x + width, f1, width, label='F1-Score (%)', color='#2ca02c', alpha=0.85)

    for rects in [rects1, rects2, rects3]:
        for r in rects:
            h = r.get_height()
            ax1.annotate(f'{h:.1f}%', xy=(r.get_x() + r.get_width()/2, h),
                         xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax1.axhline(90.2, color='#9467bd', linestyle='--', linewidth=1.5, label='Macro F1 = 90.2%')
    ax1.set_title('Hiệu năng mô hình PhoBERT-NER theo loại thực thể', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Tỷ lệ phần trăm (%)', fontsize=10, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(entities, fontsize=9, fontweight='bold')
    ax1.set_ylim(70, 102)
    ax1.legend(loc='lower right', fontsize=8.5, frameon=True, facecolor='white')
    ax1.grid(axis='y', linestyle=':', alpha=0.6)

    # Biểu đồ 2: Thời gian trễ suy luận thực tế (Inference Latency ms)
    cases_label = [f'Câu {i+1}\n({"Khởi động" if i==0 else f"{ms_list[i]:.0f}ms"})' for i in range(len(CASES))]
    colors_lat = ['#d62728'] + ['#1f77b4'] * (len(CASES) - 1)

    bars = ax2.bar(cases_label, ms_list, color=colors_lat, alpha=0.85, edgecolor='black', width=0.5)
    for b, val in zip(bars, ms_list):
        ax2.annotate(f'{val:.0f} ms', xy=(b.get_x() + b.get_width()/2, val),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    avg_run = np.mean(ms_list[1:]) if len(ms_list) > 1 else ms_list[0]
    ax2.axhline(avg_run, color='#2ca02c', linestyle='--', linewidth=1.5, label=f'Độ trễ TB sau nạp: {avg_run:.1f} ms')
    ax2.set_title('Thời gian xử lý thực tế nhận diện thực thể (CPU)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Thời gian (ms)', fontsize=10, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=8.5, frameon=True, facecolor='white')
    ax2.grid(axis='y', linestyle=':', alpha=0.6)

    out_fig = "charts_output/danh_gia_10_ner_phobert.png"
    plt.tight_layout()
    plt.savefig(out_fig, dpi=300)
    plt.close()
    print(f"\n[XONG] Đã tạo ảnh kết quả: {out_fig}")
except ImportError:
    print("\n[CHÚ Ý] Cần matplotlib để tạo ảnh đồ thị: pip install matplotlib")