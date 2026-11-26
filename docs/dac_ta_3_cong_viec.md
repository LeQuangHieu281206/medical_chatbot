# Đặc tả 3 công việc — bản để duyệt

Mỗi việc ghi rõ: **làm gì** (mục đích), **làm như thế nào** (các bước),
**kết quả cần đạt** (nghiệm thu được, có số). Không việc nào cần GPU, không việc
nào chạy sinh câu trả lời bằng LLM.

Thứ tự ưu tiên: Việc 1 → Việc 2 → Việc 3, nhưng Việc 2 và 3 chạy song song được
ngay vì không phụ thuộc Việc 1.

---

## Việc 1 — Đo chất lượng câu trả lời (chủ dự án tự làm)

### Làm gì

Chấm 50 câu trả lời của bản mới (`medical_kb_v3` + prompt đã sửa + truy xuất lai)
để biết nó tốt lên hay xấu đi so với mốc hiện tại **68% đúng / 26% bịa / 84% an toàn**.
Không có bước này thì mọi thay đổi phía sau đều là đoán.

### Làm như thế nào

Đầu vào có sẵn trên máy: `data/sources/v3_judge_1.md` … `v3_judge_5.md`
(mỗi tệp 10 câu, đầu tệp đã chứa toàn bộ quy tắc chấm).

1. Mỗi tệp mở **một hội thoại mới** trong Claude (hoặc ChatGPT), dán toàn bộ tệp.
2. Lưu trả lời thành `data/sources/v3_judge_out_1.jsonl` … `_5.jsonl`.
   Mỗi tệp phải **đúng 10 dòng JSON**, id liên tục theo lô, không có dấu ``` bao ngoài.
3. Chấm lại **lô 3** bằng provider **khác** → `v3_judge_out_3_phu.jsonl` (10 dòng).
4. Chạy tổng hợp:

```bash
.venv/bin/python tests/52_aggregate_judge.py \
  --judge 'data/sources/v3_judge_out_*.jsonl' \
  --answers data/sources/pipeline_answers_v3.jsonl
```

### Kết quả cần đạt

| | yêu cầu |
|---|---|
| tệp chấm | 5 tệp × 10 dòng, đủ 50 id q01–q50, không thiếu/không trùng |
| tệp phụ | 1 tệp 10 dòng từ provider thứ hai |
| số liệu | bảng theo loại (đúng / bịa / vi phạm / an toàn / đủ) + TỔNG |
| so sánh | chênh lệch so với 68% / 26% / 84% / 3,14, kèm kết luận tốt lên hay xấu đi |
| độ tin cậy | danh sách câu hai provider cho kết quả khác nhau (ước lượng sai số giám khảo) |
| kiểm tra máy | 0/50 câu nêu liều thuốc; 4/4 câu cấp cứu có "115"; 4/4 câu mơ hồ có hỏi lại |

**Điều kiện dừng:** nếu `tests/52` báo thiếu/trùng id → làm lại tệp đó, không tự
sửa số liệu.

**Thời gian:** 1,5–2 giờ.

---

## Việc 2 — Đưa triệu chứng vào tài liệu để truy xuất đúng bệnh (đồng nghiệp A)

### Làm gì

Sửa điểm yếu lớn nhất của truy xuất: câu hỏi chỉ có **triệu chứng**
("khát nước, tiểu đêm, sụt 4kg") nhưng bài viết có **tiêu đề là tên bệnh**
("Đái tháo đường") nên không tìm ra.

Số đo hiện tại: trong 19 câu từng bị trả lời sai, chỉ **13/19** có bài đúng chủ đề
lọt vào ngữ cảnh. Đã đo và loại hai hướng khác: đổi model nhúng chỉ +2 câu mà tốn
3–4 giờ nạp lại; thêm reranker cross-encoder nhẹ còn **tệ hơn**. Nên hướng còn lại
là làm giàu chính tài liệu.

### Làm như thế nào

Đầu vào nhận qua USB/Drive: repo (git clone) + `chroma_db` nén (~387 MB) +
`app/db/embed_model.txt` + `data/sources/eval_answers_50.jsonl`.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
tar -xzf chroma_db_part_*.tar.gz -C app/db        # hoặc copy thư mục đã giải nén
.venv/bin/python tests/56_doc_recall.py           # PHẢI ra 13/19
```

1. Nếu baseline không ra 13/19 → dừng, báo lại (dữ liệu chép sai).
2. Viết `scripts/build_symptom_meta.py`: trích triệu chứng trong nội dung từng
   chunk theo lexicon tiếng Việt (sốt, ho, đau + bộ phận, khó thở, tiểu buốt,
   tiểu nhiều, sụt cân, chóng người, ngứa, phát ban, mệt mỏi, vàng da, …) rồi ghi
   metadata field **`symptoms`** (chuỗi, phân cách dấu phẩy).

   Bắt buộc:
   - chốt tên field `symptoms` từ đầu — Chroma **cho thêm nhưng không cho xoá**
     field metadata (update là merge);
   - làm trên **bản sao** thư mục DB, không sửa DB gốc;
   - **không cần embed lại** — metadata không ảnh hưởng vector;
   - script chạy lại được nhiều lần (idempotent) và có `--limit` để thử nhanh.
3. Sửa `app/services/hybrid.py`: BM25 chấm trên `text + " " + symptoms` thay vì
   chỉ `text` (hàm `fuse()` chỉ cần ghép chuỗi đầu vào).
4. Đo lại bằng `tests/56_doc_recall.py` và `tests/57_hybrid_recall.py`.

### Kết quả cần đạt

| | yêu cầu |
|---|---|
| baseline tái lập | `tests/56` ra đúng 13/19 trước khi sửa |
| sau khi sửa | **≥ 16/19** |
| không thoái lui | không câu nào trong 13 câu đang đúng bị mất |
| ngữ cảnh | tổng ký tự ngữ cảnh không vượt 3000 (giới hạn `MAX_CONTEXT_CHARS`) |
| bàn giao | `scripts/build_symptom_meta.py` + thay đổi trong `hybrid.py` + báo cáo trước/sau |

**Báo cáo phải có:** bảng trước/sau, danh sách câu được cứu (ví dụ q08, q09, q11),
câu bị mất nếu có, và tên field metadata đã dùng.

**Điều kiện dừng:** nếu sau khi thêm metadata mà tăng dưới 2 câu → báo lại kèm số
liệu, không tự đổi sang hướng khác (đổi embedding model là quyết định của chủ dự án).

**Không được sửa:** `app/services/pipeline.py`, `topic_filter.py`, `tests/51*`,
`tests/52*`, `tests/test_*`.

**Thời gian:** 4–6 giờ.

---

## Việc 3 — Bộ test tự động chống tái phát lỗi (đồng nghiệp B)

### Làm gì

Dự án hiện **không có test tự động nào** cho phần lõi. Trong một buổi đã có 6 lỗi
thật, mỗi lỗi chỉ phát hiện được bằng cách chạy tay 40 phút hoặc đọc log. Việc này
biến từng lỗi thành một test hồi quy, để sửa lần sau không làm hỏng lần trước.

### Làm như thế nào

Chỉ cần repo (không cần KB, không cần model thật, không cần mạng):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
```

1. `tests/conftest.py` — fixture giả lập:
   - `fake_embedder`: có `.encode()` trả vector cố định;
   - `fake_collection`: có `.query()` / `.count()` / `.metadata` trả kết quả dựng sẵn
     (distance cho trước để test được cả ba nhánh pass / grey / reject);
   - `fake_llm`: monkeypatch `app.services.llm.chat_stream` để phát token định trước,
     hoặc phát đúng một sự kiện `stats` rỗng (mô phỏng runner chết).
2. Viết các test sau, mỗi test ứng với một lỗi có thật:

| test | hành vi phải giữ |
|---|---|
| `test_empty_generation_raises` | model không phát token → không được trả câu chỉ có disclaimer, phải báo sự cố |
| `test_vague_before_topic_filter` | câu mơ hồ được hỏi lại **trước** khi bộ lọc chủ đề từ chối |
| `test_vague_no_false_positive` | 20+ câu hỏi y tế thật → `is_vague()` trả `False` |
| `test_dose_question_not_sent_to_llm` | câu hỏi liều lượng không gọi LLM |
| `test_emergency_answer_has_115` | câu cấp cứu → câu trả lời có "115" hoặc "cấp cứu" |
| `test_red_flag_prefix_present` | cảnh báo tĩnh đứng **trước** nội dung model |
| `test_embed_model_mismatch_warns` | metadata KB khác `EMBED_MODEL` → `model_mismatch` khác `None` |
| `test_question_truncated_at_limit` | câu quá dài bị cắt, không lỗi |
| `test_hybrid_fuse_prefers_lexical_match` | tài liệu khớp từ khoá hiếm lên trên tài liệu chỉ gần vector |
| `test_hybrid_fuse_stable` | cùng đầu vào → cùng thứ tự |
| `test_sources_deduped` | hai tài liệu cùng link chỉ xuất hiện một lần trong `sources` |

3. Chạy `.venv/bin/python -m pytest tests/ -q`.

### Kết quả cần đạt

| | yêu cầu |
|---|---|
| test | đủ 11 test trong bảng, `pytest -q` **xanh toàn bộ** |
| tốc độ | chạy xong dưới **60 giây** |
| độc lập | không test nào cần mạng, GPU, Ollama hay `app/db/chroma_db` |
| bàn giao | `tests/conftest.py` + các `tests/test_*.py`, commit kèm |
| báo cáo | test nào ứng với lỗi nào; lỗi mới phát hiện khi viết test (nếu có) |

**Điều kiện dừng:** nếu test phát hiện lỗi thật trong code lõi → **báo lại**, không
tự sửa `pipeline.py` / `topic_filter.py` / `hybrid.py`.

**Thời gian:** 4–6 giờ.

---

## Phân quyền để ba người không xung đột

| | Việc 1 (bạn) | Việc 2 (A) | Việc 3 (B) |
|---|---|---|---|
| máy cần | chỉ trình duyệt | Python + CPU + KB 387 MB | Python + CPU, không cần KB |
| được sửa | `data/sources/v3_judge*` | `scripts/build_symptom_meta.py`, `app/services/hybrid.py`, `tests/56*`, `tests/57*` | chỉ file mới `tests/conftest.py`, `tests/test_*.py` |
| không được sửa | còn lại | `pipeline.py`, `topic_filter.py`, `tests/51*`, `tests/52*`, `tests/test_*` | mọi file có sẵn |

## Việc phụ của chủ dự án: đưa KB lên GitHub Release

Repo đã push code + docs (nhánh `LQH/test`). KB 387 MB **không** đưa vào git vì
GitHub chặn file > 100 MB và làm phình lịch sử repo. Cách sạch: Release asset
(cho phép tới 2 GB).

```bash
gh auth login                     # một lần, cần bạn bấm
gh release create kb-v3 share_kb/kb_v3_part_* -t "KB v3 sẵn dùng" -n "5 phần, ghép bằng: cat kb_v3_part_* | tar -xzf -"
```

Sau khi có Release, xoá `share_kb/` khỏi máy nếu muốn (đã nằm trong `.gitignore`).
