"""
Script vẽ đồ thị trực quan hóa kết quả đánh giá thực nghiệm Chatbot Y Tế
Tương thích hoàn hảo với Google Colab và môi trường Python cục bộ.
Tự động lưu ảnh 300 DPI và đóng gói thành bieu_do_danh_gia.zip
"""

import os
import zipfile
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ============================================================
# 1. CẤU HÌNH GIAO DIỆN VÀ FONT CHỮ (HỖ TRỢ TIẾNG VIỆT ĐẸP)
# ============================================================
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.autolayout'] = True
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

OUTPUT_DIR = "charts_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Bảng màu chuẩn khoa học
COLOR_PRIMARY = "#1f77b4"     # Xanh dương đậm
COLOR_SUCCESS = "#2ca02c"     # Xanh lá cây
COLOR_DANGER = "#d62728"      # Đỏ
COLOR_WARNING = "#ff7f0e"     # Cam
COLOR_PURPLE = "#9467bd"      # Tím
COLOR_GRAY = "#7f7f7f"        # Xám


# ============================================================
# HÌNH 3.1: PHÂN BỐ KHOẢNG CÁCH VECTOR COSINE TOP-1 & NGƯỠNG LỌC
# ============================================================
def draw_chart_1():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    # Dữ liệu mô phỏng theo đúng phân bố thực nghiệm (Bảng 3.1)
    np.random.seed(42)
    d_eval = np.clip(np.random.normal(0.084, 0.021, 500), 0.042, 0.143)
    d_short = np.array([0.064, 0.066, 0.068, 0.072, 0.075, 0.080, 0.080, 0.080, 
                        0.082, 0.087, 0.090, 0.091, 0.093, 0.102, 0.115])
    d_off = np.array([0.132, 0.136, 0.143, 0.146, 0.151, 0.154, 0.155, 0.155, 
                      0.155, 0.155, 0.155, 0.161, 0.162, 0.164, 0.172, 0.174, 
                      0.176, 0.176, 0.181, 0.181, 0.181, 0.186, 0.192, 0.195, 0.196, 0.234])
    d_border = np.array([0.087, 0.093, 0.098, 0.108, 0.109, 0.138, 0.157, 0.160])

    data = [d_eval, d_short, d_border, d_off]
    labels = [
        'Y tế chuẩn\n(Eval - 500 câu)', 
        'Y tế ngắn\n(15 câu)', 
        'Ranh giới\n(8 câu)', 
        'Ngoài chủ đề\n(Off-topic - 26 câu)'
    ]
    colors = [COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER]

    # Vẽ vùng phân chia 3 phân vùng (Pass zone, Grey zone, Reject zone)
    ax.axhspan(0.04, 0.12, color='#e8f5e9', alpha=0.8, label='Vùng an toàn (Pass Zone: d <= 0.12)')
    ax.axhspan(0.12, 0.14, color='#fff9c4', alpha=0.8, label='Vùng xám phân loại LLM (Grey Zone: 0.12 < d <= 0.14)')
    ax.axhspan(0.14, 0.25, color='#ffebee', alpha=0.8, label='Vùng chặn trực tiếp (Reject Zone: d > 0.14)')

    # Vẽ Boxplot
    box = ax.boxplot(data, patch_artist=True, labels=labels, widths=0.45,
                     medianprops=dict(color='black', linewidth=1.8),
                     flierprops=dict(marker='o', markersize=5, alpha=0.5))
    
    for patch_item, color in zip(box['boxes'], colors):
        patch_item.set_facecolor(color)
        patch_item.set_alpha(0.7)

    # Vẽ đường ngưỡng
    ax.axhline(0.12, color='green', linestyle='--', linewidth=1.8, label='Ngưỡng PASS_MAX = 0.12')
    ax.axhline(0.14, color='red', linestyle='--', linewidth=1.8, label='Ngưỡng REJECT_MIN = 0.14')

    ax.set_title('Hình 3.1: Phân bố khoảng cách vector Cosine Top-1 và cơ chế lọc chủ đề 3 vùng', 
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_ylabel('Khoảng cách Cosine đến tài liệu gần nhất (d)', fontsize=11, fontweight='bold')
    ax.set_ylim(0.03, 0.25)
    ax.legend(loc='upper left', frameon=True, fontsize=9, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle=':', alpha=0.6)

    path = os.path.join(OUTPUT_DIR, 'hinh_3_1_phan_bo_khoang_cach.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Đã lưu: {path}")


# ============================================================
# HÌNH 3.2: ĐƯỜNG CONG ĐÁNH ĐỔI ĐỘ NHẠY VÀ ĐẶC HIỆU THEO NGƯỠNG LỌC
# ============================================================
def draw_chart_2():
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

    thresholds = [0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16]
    med_pass_rate = [78.0, 89.4, 96.6, 98.8, 99.6, 100.0, 100.0]
    off_reject_rate = [100.0, 100.0, 100.0, 100.0, 92.3, 84.6, 57.7]

    ax.plot(thresholds, med_pass_rate, marker='s', color=COLOR_SUCCESS, linewidth=2.5, 
            markersize=7, label='Tỷ lệ câu hỏi y tế cho qua (Độ phủ %)')
    ax.plot(thresholds, off_reject_rate, marker='o', color=COLOR_DANGER, linewidth=2.5, 
            markersize=7, label='Tỷ lệ câu ngoài chủ đề bị chặn (Độ an toàn %)')

    # Điểm tối ưu 0.12 và 0.14
    ax.scatter([0.12], [96.6], color='green', s=120, zorder=5)
    ax.scatter([0.12], [100.0], color='green', s=120, zorder=5)
    ax.annotate('Ngưỡng PASS_MAX = 0.12\n(Phủ 96.6% y tế, Chặn 100% ngoài lề)', 
                xy=(0.12, 96.6), xytext=(0.102, 88),
                arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.2),
                fontsize=9.5, fontweight='bold', backgroundcolor='white')

    ax.scatter([0.14], [92.3], color='red', s=120, zorder=5)
    ax.annotate('Ngưỡng REJECT_MIN = 0.14\n(Chặn 92.3% câu xa)', 
                xy=(0.14, 92.3), xytext=(0.135, 78),
                arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.2),
                fontsize=9.5, fontweight='bold', backgroundcolor='white')

    ax.set_title('Hình 3.2: Khảo sát độ nhạy và cân bằng tối ưu theo các ngưỡng khoảng cách lọc', 
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel('Ngưỡng khoảng cách Cosine (t)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Tỷ lệ phần trăm (%)', fontsize=11, fontweight='bold')
    ax.set_ylim(50, 105)
    ax.set_xticks(thresholds)
    ax.legend(loc='lower left', frameon=True, fontsize=10, facecolor='white')
    ax.grid(True, linestyle=':', alpha=0.6)

    path = os.path.join(OUTPUT_DIR, 'hinh_3_2_duong_cong_nguong_loc.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Đã lưu: {path}")


# ============================================================
# HÌNH 3.3: SO SÁNH HIỆU NĂNG TRUY XUẤT RAG (ĐOẠN VĂN VS BÀI VIẾT)
# ============================================================
def draw_chart_3():
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

    metrics = ['Recall@1', 'Recall@2', 'Recall@3', 'Recall@10', 'MRR@10']
    passage_scores = [73.6, 84.6, 88.6, 96.8, 81.2]
    article_scores = [85.2, 91.8, 94.4, 98.2, 89.1]

    x = np.arange(len(metrics))
    width = 0.35

    rects1 = ax.bar(x - width/2, passage_scores, width, label='Mức đoạn văn (Passage-level)', 
                    color=COLOR_PRIMARY, alpha=0.85, edgecolor='black')
    rects2 = ax.bar(x + width/2, article_scores, width, label='Mức bài viết gốc (Article-level)', 
                    color=COLOR_PURPLE, alpha=0.85, edgecolor='black')

    # Thêm nhãn giá trị trên đầu cột
    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f'{h:.1f}%' if h > 1 else f'{h:.3f}',
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f'{h:.1f}%' if h > 1 else f'{h:.3f}',
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='#4a148c')

    ax.set_title('Hình 3.3: So sánh độ phủ truy xuất RAG giữa mức đoạn văn và mức bài viết (500 câu ViMedAQA)', 
                 fontsize=12, fontweight='bold', pad=15)
    ax.set_ylabel('Tỷ lệ Recall@K (%) / Điểm MRR', fontsize=11, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=10, fontweight='bold')
    ax.set_ylim(60, 105)
    ax.legend(loc='lower right', frameon=True, fontsize=10, facecolor='white')
    ax.grid(axis='y', linestyle=':', alpha=0.6)

    path = os.path.join(OUTPUT_DIR, 'hinh_3_3_truy_xuat_rag.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Đã lưu: {path}")


# ============================================================
# HÌNH 3.4: KẾT QUẢ ĐÁNH GIÁ ĐẦU-CUỐI TRÊN 52 CÂU HỎI THỰC TẾ
# ============================================================
def draw_chart_4():
    fig, ax1 = plt.subplots(figsize=(11, 6), dpi=300)

    groups = [
        'Triệu chứng\n(sym - 12)', 
        'Tra cứu thuốc\n(drug - 10)', 
        'Liều dùng\n(dose - 4)', 
        'Cấp cứu 115\n(emg - 4)', 
        'Dinh dưỡng\n(nut - 6)', 
        'Đối tượng nhạy\n(kid - 4)', 
        'Ngoài chủ đề\n(off - 6)', 
        'Mơ hồ, ngắn\n(vague - 4)', 
        'Ngoài KB\n(oov - 2)'
    ]
    pass_rates = [100.0, 70.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 0.0]
    avg_times = [41.6, 19.6, 0.7, 35.2, 38.4, 31.5, 0.4, 31.2, 0.0]

    x = np.arange(len(groups))
    width = 0.45

    # Cột tỷ lệ đạt (trục bên trái)
    bars = ax1.bar(x, pass_rates, width, color=COLOR_PRIMARY, alpha=0.8, edgecolor='black', label='Tỷ lệ đạt yêu cầu (%)')
    ax1.set_ylabel('Tỷ lệ câu trả lời đạt chuẩn (%)', color=COLOR_PRIMARY, fontsize=11, fontweight='bold')
    ax1.set_ylim(0, 115)
    ax1.tick_params(axis='y', labelcolor=COLOR_PRIMARY)

    for bar, val in zip(bars, pass_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, val + 2, f'{val:.0f}%', 
                 ha='center', va='bottom', fontsize=9, fontweight='bold', color=COLOR_PRIMARY)

    # Đường thời gian trung bình (trục bên phải)
    ax2 = ax1.twinx()
    line = ax2.plot(x, avg_times, color=COLOR_DANGER, marker='o', linewidth=2.5, markersize=8, label='Thời gian xử lý TB (giây)')
    ax2.set_ylabel('Thời gian phản hồi trung bình trên CPU (giây)', color=COLOR_DANGER, fontsize=11, fontweight='bold')
    ax2.set_ylim(0, 50)
    ax2.tick_params(axis='y', labelcolor=COLOR_DANGER)
    ax2.grid(False)

    for i, t in enumerate(avg_times):
        ax2.annotate(f'{t:.1f}s', xy=(x[i], t), xytext=(0, 8), textcoords="offset points",
                     ha='center', fontsize=9, fontweight='bold', color=COLOR_DANGER)

    ax1.set_title('Hình 3.4: Tỷ lệ đạt chuẩn và thời gian phản hồi theo 9 nhóm kịch bản kiểm thử (52 câu hỏi)', 
                 fontsize=12, fontweight='bold', pad=15)
    ax1.set_xticks(x)
    ax1.set_xticklabels(groups, fontsize=9.5, fontweight='bold')
    
    # Hợp nhất chú thích
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', frameon=True, facecolor='white')

    path = os.path.join(OUTPUT_DIR, 'hinh_3_4_danh_gia_52_cau.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Đã lưu: {path}")


# ============================================================
# HÌNH 3.5: HIỆU NĂNG TÍNH TOÁN CỦA QWEN 3.5 4B TRÊN CPU
# ============================================================
def draw_chart_5():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), dpi=300)

    configs = [
        'num_ctx: 4096 (chuẩn)',
        'num_ctx: 2560',
        'num_ctx: 2560 (4 threads)',
        'num_ctx: 2560 (8 threads)'
    ]
    prompt_speeds = [99.1, 97.5, 99.8, 98.8]
    gen_speeds = [5.2, 5.4, 4.8, 4.9]

    y = np.arange(len(configs))

    # Đồ thị 1: Tốc độ xử lý Context
    bars1 = ax1.barh(y, prompt_speeds, height=0.45, color=COLOR_PRIMARY, alpha=0.85, edgecolor='black')
    ax1.set_title('Tốc độ nạp Prompt Context\n(prompt tokens / giây)', fontsize=11, fontweight='bold')
    ax1.set_yticks(y)
    ax1.set_yticklabels(configs, fontsize=9.5, fontweight='bold')
    ax1.set_xlim(80, 110)
    ax1.set_xlabel('Token / giây (càng cao càng nhanh)', fontsize=10)
    for b in bars1:
        w = b.get_width()
        ax1.text(w + 0.5, b.get_y() + b.get_height()/2, f'{w:.1f}', va='center', fontsize=9, fontweight='bold')
    ax1.grid(axis='x', linestyle=':', alpha=0.6)

    # Đồ thị 2: Tốc độ sinh chữ
    bars2 = ax2.barh(y, gen_speeds, height=0.45, color=COLOR_SUCCESS, alpha=0.85, edgecolor='black')
    ax2.set_title('Tốc độ sinh câu trả lời trên CPU\n(eval tokens / giây)', fontsize=11, fontweight='bold')
    ax2.set_yticks(y)
    ax2.set_yticklabels([])
    ax2.set_xlim(3.5, 6.2)
    ax2.set_xlabel('Token / giây (~3-4 từ tiếng Việt/s)', fontsize=10)
    for b in bars2:
        w = b.get_width()
        ax2.text(w + 0.05, b.get_y() + b.get_height()/2, f'{w:.1f} tok/s', va='center', fontsize=9, fontweight='bold')
    ax2.grid(axis='x', linestyle=':', alpha=0.6)

    fig.suptitle('Hình 3.5: Đo đạc tốc độ xử lý của mô hình Qwen 3.5 4B qua Ollama trên môi trường CPU', 
                 fontsize=13, fontweight='bold', y=1.02)

    path = os.path.join(OUTPUT_DIR, 'hinh_3_5_hieu_nang_cpu.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Đã lưu: {path}")


def package_zip():
    zip_path = "bieu_do_danh_gia.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(OUTPUT_DIR):
            for file in files:
                if file.endswith('.png'):
                    zipf.write(os.path.join(root, file), file)
    print(f"\n[HOÀN THÀNH] Đã đóng gói toàn bộ ảnh vào tệp: {zip_path}")


if __name__ == "__main__":
    print("=== BẮT ĐẦU TẠO 5 BIỂU ĐỒ BÁO CÁO KHOA HỌC ===")
    draw_chart_1()
    draw_chart_2()
    draw_chart_3()
    draw_chart_4()
    draw_chart_5()
    package_zip()
