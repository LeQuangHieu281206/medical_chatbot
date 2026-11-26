# Triển khai trên máy mới (kể cả khi clone từ GitHub)

## Điều quan trọng nhất: repo KHÔNG chứa KB và không chứa model

`.gitignore` đang loại các thứ rất nặng:

| Đường dẫn | Dung lượng | Vì sao không commit |
|---|---|---|
| `app/db/chroma_db/` | ~741 MB | vector DB, sinh lại được |
| `models/` | ~1,9 GB | cache model của `sentence-transformers` |
| `data/processed/`, `data/raw/` | vài trăm MB | dữ liệu trung gian |

Nên người pull về **có code nhưng chưa có KB**. Muốn dùng phải nạp KB một lần
(mất 1–2 giờ trên CPU, tự tải model từ HuggingFace, cần internet).

## Các bước cho máy mới

```bash
git clone <repo> && cd medical_chatbot
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # điền GEMINI_API_KEY nếu muốn dùng Gemini

# 1) Nạp kho hỏi đáp (Q&A)
.venv/bin/python app/services/ingest_kb.py \
    --kb data/processed/kb_merged_v3.jsonl --collection medical_kb_v3

# 2) Nạp kho bách khoa (bài viết y khoa)
.venv/bin/python app/services/ingest_kb.py \
    --kb data/processed/kb_vimedaqa.jsonl --collection medical_kb_vimedaqa

# 3) Chạy
.venv/bin/python -m uvicorn app.api.server:app --port 8000
cd frontend && npm install && npm run dev
```

Bước 1 cần `data/processed/kb_merged_v3.jsonl` (sinh từ `scripts/build_kb_merged.py`
trên dữ liệu nguồn trong `data/raw/`). Bước 2 tự tải ViMedAQA từ HuggingFace

## Nếu đổi model nhúng (embedding)

Đổi được bằng biến môi trường, **nhưng phải làm đủ 3 việc**, nếu không hệ thống
sẽ trả lời sai mà không báo lỗi:

```bash
export EMBED_MODEL="dangvantuan/vietnamese-embedding"

# (1) nạp lại TOÀN BỘ KB — không trộn được vector của hai model
.venv/bin/python app/services/ingest_kb.py --kb ... --collection medical_kb_v3_new

# (2) trỏ sang collection mới
export KB_COLLECTION=medical_kb_v3_new

# (3) hiệu chuẩn lại ngưỡng lọc chủ đề cho model mới
python tests/48_calibrate_distance.py
export TOPIC_PASS_MAX=<đo được> TOPIC_REJECT_MIN=<đo được>
```

Vì sao phải chuẩn hoá lại: mỗi model có thang khoảng cách khác nhau. Ngưỡng
0.12/0.14 hiện tại là của `intfloat/multilingual-e5-small`; dùng cho model khác
sẽ từ chối oan câu y tế hoặc cho lọt câu ngoài chủ đề.

## Chống lỗi "KB cũ + model mới"

`app/db/embed_model.txt` ghi model đã dùng để nhúng KB (mỗi lần ingest tự ghi).
Lúc mở KB, `TopicFilter` so với `EMBED_MODEL` và in cảnh báo nếu lệch:

```
[topic_filter] CẢNH BÁO: KB [medical_kb_v3] được nhúng bằng 'X' nhưng đang cấu hình 'Y'.
```

Đây là loại lỗi nguy hiểm nhất vì vector vẫn "chạy" bình thường nhưng kết quả
truy xuất là rác — không có exception nào để lần ra.

## Biến môi trường liên quan

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `KB_COLLECTION` | `medical_kb_v3` | collection kho hỏi đáp |
| `KB_ENCY_COLLECTION` | `medical_kb_vimedaqa` | collection bài viết y khoa |
| `EMBED_MODEL` | `intfloat/multilingual-e5-small` | model nhúng (phải khớp KB) |
| `TOPIC_PASS_MAX` / `TOPIC_REJECT_MIN` | `0.12` / `0.14` | ngưỡng lọc chủ đề |
| `HYBRID_RETRIEVAL` | `1` | dense + BM25-RRF |
| `QUERY_EXPAND` | `0` | mở rộng truy vấn bằng tên bệnh (đo chưa đủ tốt) |
| `GEMINI_API_KEY` | — | bật provider Gemini |

## Kiểm tra sau khi nạp KB

```bash
.venv/bin/python tests/56_doc_recall.py    # tài liệu đúng chủ đề có vào ngữ cảnh không
```
