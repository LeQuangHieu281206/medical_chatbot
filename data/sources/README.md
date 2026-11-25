# Dữ liệu gốc (chưa qua xử lý)

Thư mục này chứa dữ liệu **nguồn** do người dùng cấp. Code KHÔNG đọc trực tiếp ở đây;
`app/services/normalizer.py` chỉ đọc bản đã gộp/chuẩn hoá trong `data/processed/`.

## Bảng viết tắt / teencode / chính tả

| File | Nội dung | Trạng thái |
|---|---|---|
| `vietnamese_medical_abbreviations_expanded.csv` | 350 viết tắt y tế, 4 cột (có `bien_the_go`) | **đang dùng** → `data/processed/abbrev_yte_mo_rong.csv` |
| `cap_tu_nham_chinh_ta_tieng_viet.csv` | 530 cặp từ dễ nhầm | gộp vào `data/processed/confusion_vi.csv` |
| `vietnamese_spelling_errors.csv` | 519 cặp từ dễ nhầm (bổ sung) | gộp vào `data/processed/confusion_vi.csv` |
| `vietnamese_medical_teencode.csv` | 294 teencode y tế | gộp vào `data/processed/teencode_vi.csv` |
| `teencode_viet_tat_chat_y_te.csv` | 299 teencode/viết tắt chat | gộp vào `data/processed/teencode_vi.csv` |

Hai bảng chính tả **bổ sung cho nhau**, không phải bản sao: hợp = 933 cặp, giao = 116.
Chúng là danh sách cặp *đối xứng* (466 cặp có cả hai chiều), nên chỉ dùng làm ứng viên +
bảo vệ từ đã đúng, KHÔNG được ép thay một chiều.

## Bộ đánh giá

| File | Nội dung |
|---|---|
| `eval_chuan_hoa_cau_hoi_y_te.jsonl` | 400 câu thật, khoá `clean/noisy/loai`; phân bố: sach 30, khong_dau 90, viet_tat 80, sai_chinh_ta 90, sai_dau 50, tron 60 |

## Corpus

| Thư mục | Nội dung |
|---|---|
| `data/corpus/` | 300.000 câu thật (fineweb-2 + Wikipedia), sinh bằng `build_vietnamese_corpus.py`. **Đây là nguồn dựng lexicon.** |
| `corpus_mau/` | 300.000 dòng do nguồn khác cấp. Văn bản mẫu lặp: 45.205 từ duy nhất ở bộ thật so với rất thấp ở đây; nhiều từ thông dụng có tần suất 0 (`mười`, `im`, `top`). **Không dùng** — giữ để tham chiếu, xoá được nếu không cần: `rm -rf data/sources/corpus_mau`. |

## Ghi chú khi cập nhật dữ liệu

Hai lỗi thực tế đã gặp khi gộp bảng teencode, cần kiểm tra lại mỗi lần thêm dữ liệu:

1. **Khoá chỉ là chính tả không dấu của chính nghĩa** (`khong` → `không`, `dau` → `đau`):
   đưa vào sẽ làm hỏng câu đã có dấu. Bộ khôi phục dấu đã xử lý nhóm này.
2. **Khoá trùng một âm tiết tiếng Việt thật** (`va` = `và`, `a` = `ạ`, `cho` = `chợ`):
   nếu là cụm nhiều từ thì phải có `khong_mo_rong`, nếu không luật che khuất sẽ loại.
3. **Khoá đa nghĩa** (`tk` = tái khám / thần kinh / cảm ơn): không thể quyết nếu thiếu
   ngữ cảnh, nên bỏ khỏi bảng thay vì đoán.
