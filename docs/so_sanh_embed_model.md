# So sánh model nhúng — kết quả đo (mức tiêu đề)

Đo bằng `tests/58_embed_compare.py --sample 5000` trên `medical_kb_v3`:
6.387 tiêu đề (toàn bộ tiêu đề khớp bệnh + mẫu ngẫu nhiên), 19 câu hỏi từng bị
trả lời sai. Câu hỏi chỉ mô tả triệu chứng; đáp án đúng là bài có TIÊU ĐỀ tên bệnh.

| model | dim | top-3 | top-10 | thời gian embed | thiếu top-3 |
|---|---|---|---|---|---|
| `intfloat/multilingual-e5-small` (đang dùng) | 384 | 10/19 | 15/19 | 164s | q02 q05 q07 q08 q09 q11 q12 q15 q22 |
| `keepitreal/vietnamese-sbert` | 768 | **12/19** | **16/19** | 460s | q04 q05 q07 q09 q11 q12 q15 |
| `dangvantuan/vietnamese-embedding` | 768 | 9/19 | 14/19 | 469s | q02 q03 q04 q05 q07 q09 q11 q12 q14 q15 |

## Kết luận

- Model tốt nhất trong 3 cái chỉ hơn hiện tại **+2 câu top-3** (10 → 12) và
  **+1 câu top-10**.
- Đổi sang nó tốn: nạp lại 43k chunk trên CPU (~3–4 giờ, model chậm 2,8 lần),
  hiệu chuẩn lại `TOPIC_PASS_MAX`/`TOPIC_REJECT_MIN`, và máy hiện chỉ còn
  ~6GB RAM trống (PhoBERT đã gây treo khi chạy 25k tiêu đề).
- `dangvantuan/vietnamese-embedding` **tệ hơn** e5-small → loại.

**Khuyến nghị: chưa đổi model nhúng.** Tỉ lệ đổi/chi phí không đáng, và nút cổ
chai thật nằm ở chỗ khác: bài viết có tiêu đề tên bệnh, câu hỏi chỉ có triệu
chứng — nên bổ sung chỉ mục triệu chứng (metadata) hoặc bảng ánh xạ
triệu chứng → tên bệnh, rẻ hơn nhiều và không phải nạp lại vector.

Ghi chú kỹ thuật: PhoBERT/RoBERTa giới hạn 258 vị trí, tiêu đề hỏi đáp dài hơn
gây `index out of bounds for dimension 1`; `tests/58` đã cắt `max_seq_length=256`.
