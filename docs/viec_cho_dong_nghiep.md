# 2 việc giao đồng nghiệp — chạy trên máy riêng

Việc 1 (chấm điểm) do chủ dự án tự làm. Đồng nghiệp nhận **Việc 2** và **Việc 3**.

Cả hai việc **không cần GPU, không cần Ollama**, không tranh máy chính và không
giẫm file của nhau. Chỉ máy chính mới chạy sinh câu trả lời bằng LLM.

---

## Việc 1 — Chấm 50 câu và đo độ ổn định của giám khảo *(chủ dự án tự làm)*

**Người làm:** ai cẩn thận, đọc hiểu y khoa cơ bản. Không cần cài gì, không cần repo.
**Thời gian:** 1,5–2 giờ. **Cần:** tài khoản Claude hoặc ChatGPT.

### Nhận gì

5 tệp: `v3_judge_1.md` … `v3_judge_5.md` (mỗi tệp 10 câu, đầu tệp đã có sẵn toàn
bộ quy tắc chấm — không cần prompt thêm).

### Làm

1. Mở **một cuộc trò chuyện mới** cho mỗi tệp (đừng dùng lại hội thoại cũ, model
   sẽ bị ảnh hưởng lô trước).
2. Copy **toàn bộ** nội dung tệp, dán, gửi.
3. Lưu phần trả lời thành `v3_judge_out_1.jsonl` … `_5.jsonl` (đúng tên, đúng số lô).
4. Mỗi tệp phải có **đúng 10 dòng JSON**, id chạy liên tục `q01`→`q10` cho lô 1,
   `q11`→`q20` cho lô 2, … **Kiểm tra trước khi gửi lại**: đếm số dòng, xem id có
   nhảy cách không, bỏ mọi dấu ``` bao quanh.

Dòng đúng phải như thế này (một dòng, không xuống hàng):

```json
{"id":"q01","dung":true,"du":4,"bia":false,"bia_trich":"","vi_pham":false,"vi_pham_chi_tiet":"","an_toan":true}
```

### Việc phụ (quan trọng): đo độ ổn định

Chấm lại **lô 3 (10 câu)** bằng provider **khác** (nếu lô chính dùng Claude thì
lô này dùng ChatGPT), lưu thành `v3_judge_out_3_phu.jsonl`.

Rồi báo cáo: những câu nào hai provider cho kết quả **khác nhau** ở trường
`dung` hoặc `bia`. Đây là cách duy nhất biết con số chất lượng có đáng tin hay không
(hiện đã biết ít nhất 5 ca giám khảo chấm oan: q31, q34, q11, q05, q15).

### Nghiệm thu

- 5 tệp, tổng đúng 50 dòng, không thiếu/không trùng id.
- 1 tệp phụ 10 dòng từ provider thứ hai.
- Danh sách câu lệch giữa hai provider.

### Lỗi hay gặp

| hiện tượng | cách sửa |
|---|---|
| model chỉ trả 8–9 dòng | nhắn: "còn thiếu q08, q09, hãy in tiếp đúng định dạng" |
| bọc trong ```json | nhắn: "in lại, không dùng markdown fence" |
| gộp nhiều dòng thành mảng JSON | nhắn: "mỗi mục một dòng JSON riêng" |

---

## Việc 2 — Thêm metadata triệu chứng để truy xuất đúng bệnh

**Người làm:** người biết Python cơ bản. **Thời gian:** 4–6 giờ.
**Cần:** repo, Python 3.12, CPU (không cần GPU, không cần internet sau khi có DB).

### Vấn đề cần giải

Đo được: 19 câu hỏi từng bị trả lời sai thì chỉ **13/19** có bài đúng chủ đề lọt
vào ngữ cảnh. Nguyên nhân: câu hỏi chỉ mô tả **triệu chứng** ("khát nước, tiểu
đêm, sụt 4kg") còn bài viết có **tiêu đề là tên bệnh** ("Đái tháo đường"). Đổi
model nhúng chỉ +2 câu (đã đo, không đáng nạp lại 43k chunk), nên hướng rẻ hơn là
đưa triệu chứng vào chính tài liệu.

### Nhận gì

- repo (git clone)
- thư mục `app/db/chroma_db/` (~741 MB) + `app/db/embed_model.txt` — chép vào đúng
  chỗ là dùng được, **không cần chạy ingest**, không cần tải model về trước
- `data/sources/eval_answers_50.jsonl` (bộ câu hỏi + đáp án chuẩn)

### Làm

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp -r <nơi_nhận>/chroma_db app/db/chroma_db
cp <nơi_nhận>/embed_model.txt app/db/embed_model.txt

# 1) đo lại hiện trạng — PHẢI ra 13/19, nếu không thì dừng lại báo lại
.venv/bin/python tests/56_doc_recall.py
```

2. Viết `scripts/build_symptom_meta.py`: với mỗi chunk, trích danh sách triệu
   chứng xuất hiện trong nội dung bài (lexicon tiếng Việt: sốt, ho, đau + bộ phận,
   khó thở, tiểu buốt, tiểu nhiều, sụt cân, chóng mặt, ngứa, phát ban, mệt mỏi,
   vàng da, …) rồi ghi vào metadata field **`symptoms`**.

   ```python
   col.update(ids=[...], metadatas=[{..., "symptoms": "khát nước, tiểu nhiều, sụt cân"}])
   ```

   Hai điều bắt buộc biết trước:
   - Chroma **cho thêm** field metadata nhưng **không cho xoá** (update là merge),
     nên phải chốt tên field `symptoms` và kiểu dữ liệu (chuỗi, phân cách dấu phẩy)
     ngay từ đầu.
   - Làm trên **bản sao** DB (copy thư mục ra chỗ khác rồi trỏ `DB_PATH`), đừng sửa
     DB gốc.
   - Không cần embed lại: metadata không ảnh hưởng vector.

3. Sửa `app/services/hybrid.py` để BM25 chấm trên `text + " " + symptoms` thay vì
   chỉ `text` (hàm `fuse()` đang nhận danh sách chuỗi; chỉ cần ghép thêm).

4. Đo lại:

```bash
.venv/bin/python tests/56_doc_recall.py     # mục tiêu >= 16/19
.venv/bin/python tests/57_hybrid_recall.py  # kiểm tra không tụt câu nào đang đúng
```

### Nghiệm thu

- `tests/56` trước: 13/19 (tái lập được).
- Sau: **≥ 16/19**, và **không câu nào trong 13 câu đang đúng bị mất**.
- `scripts/build_symptom_meta.py` chạy lại được từ đầu (idempotent) và có `--limit`
  để thử nhanh.
- Báo cáo ngắn: bảng trước/sau, danh sách câu được cứu, câu bị mất (nếu có).

### Không được sửa

`app/services/pipeline.py`, `app/services/topic_filter.py`, `tests/51*`, `tests/52*`,
`data/sources/v3_judge*` (của Việc 1).

---

## Cách gửi dữ liệu

| Việc 1 (bạn) | Việc 2 | Việc 3 |
|---|---|---|
| 5 tệp `v3_judge_*.md` (~100 KB) — đã có sẵn trên máy bạn | repo + `chroma_db` nén (~387 MB) + `eval_answers_50.jsonl` | chỉ repo (git clone), **không cần KB** |

Đừng gửi `models/` (1,9 GB) — `sentence-transformers` sẽ tự tải khi chạy lần đầu.


---

## Việc 3 — Bộ test tự động cho các nhánh không cần LLM

**Người làm:** người biết Python + pytest. **Thời gian:** 4–6 giờ.
**Cần:** repo + CPU. Không cần GPU, không cần Ollama, không cần KB thật (phải mock).

### Vì sao việc này

Dự án hiện **không có một test tự động nào** cho lõi xử lý. Trong một buổi đã có
6 lỗi thật, mỗi lỗi chỉ phát hiện được bằng cách chạy tay 40 phút hoặc đọc log:

1. Model không phát token → pipeline ghép mỗi câu disclaimer (149 ký tự) mà vẫn
   báo thành công.
2. Câu mơ hồ bị bộ lọc chủ đề từ chối **trước khi** kịp hỏi lại (q44).
3. Câu trả lời dị ứng không nêu dấu hiệu phản vệ.
4. Câu hỏi cấp cứu mà câu trả lời khuyên "nằm theo dõi tại nhà".
5. KB được nhúng bằng model khác model đang cấu hình → truy xuất rác, không lỗi.
6. `is_vague` từng chặn oan câu hỏi thật (phải giữ 0 dương tính giả trên 370 câu).

Mỗi mục dưới đây phải thành **một test hồi quy** để lỗi không quay lại.

### Làm

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
```

1. `tests/conftest.py` — fixture giả lập, **không gọi mạng, không nạp model thật**:
   - `fake_embedder`: object có `.encode()` trả vector cố định.
   - `fake_collection`: object có `.query()` / `.count()` / `.metadata` trả kết quả
     dựng sẵn (distance cho trước để test cả nhánh pass/grey/reject).
   - `fake_llm`: monkeypatch `app.services.llm.chat_stream` để phát chuỗi token
     định trước, hoặc phát đúng một sự kiện `stats` rỗng (mô phỏng runner chết).

2. Các test bắt buộc:

| test | hành vi phải giữ |
|---|---|
| `test_empty_generation_raises` | không có token → `ask()` **không** được trả câu chỉ có disclaimer; phải báo sự cố |
| `test_vague_before_topic_filter` | câu mơ hồ (`"Người khó chịu."`) được hỏi lại ngay cả khi bộ lọc chủ đề sẽ từ chối |
| `test_vague_no_false_positive` | 20+ câu hỏi thật (sốt, ho, đau bụng…) → `is_vague()` trả `False` |
| `test_dose_question_not_sent_to_llm` | câu hỏi liều lượng không gọi LLM, trả câu chặn có sẵn |
| `test_emergency_answer_has_115` | câu hỏi cấp cứu (đột quỵ, đau ngực) → câu trả lời có "115" hoặc "cấp cứu" |
| `test_red_flag_prefix_present` | câu khớp `red_flags` → phần cảnh báo tĩnh xuất hiện **trước** nội dung model |
| `test_embed_model_mismatch_warns` | metadata KB ghi model A, cấu hình model B → `TopicFilter.model_mismatch` khác `None` |
| `test_question_truncated_at_limit` | câu dài hơn `MAX_QUESTION_CHARS` bị cắt, không lỗi |
| `test_hybrid_fuse_prefers_lexical_match` | trong `hybrid.fuse()`, tài liệu khớp từ khoá hiếm phải lên trên tài liệu chỉ gần vector |
| `test_hybrid_fuse_stable` | cùng đầu vào → cùng thứ tự (không phụ thuộc thứ tự dict) |
| `test_sources_deduped` | hai tài liệu cùng link chỉ xuất hiện một lần trong `sources` |

3. Chạy: `.venv/bin/python -m pytest tests/ -q` phải **pass toàn bộ trong < 60 giây**.

### Nghiệm thu

- `pytest -q` xanh, ≥ 11 test trong bảng trên đều có.
- Không test nào cần mạng, GPU, Ollama, hay thư mục `app/db/chroma_db`.
- Commit kèm `tests/conftest.py` + các file `tests/test_*.py`.
- Báo cáo: test nào tương ứng lỗi nào, và **lỗi mới phát hiện khi viết test** (nếu có).

### Không được sửa

`app/services/pipeline.py`, `topic_filter.py`, `hybrid.py`, `scripts/*`, `data/sources/*`.
Chỉ thêm file trong `tests/`. Nếu test phát hiện lỗi thật trong code → báo lại,
không tự sửa code lõi.

---

## Phân quyền tổng hợp (3 việc, chạy song song được)

| | Việc 1 — bạn | Việc 2 — đồng nghiệp A | Việc 3 — đồng nghiệp B |
|---|---|---|---|
| mục tiêu | số chất lượng đáng tin | 13/19 → ≥16/19 tài liệu đúng vào ngữ cảnh | ≥11 test hồi quy, pytest xanh |
| cần máy gì | chỉ trình duyệt | Python + CPU + KB (387 MB) | Python + CPU, **không cần KB** |
| thời gian | 1,5–2 giờ | 4–6 giờ | 4–6 giờ |
| được sửa | `data/sources/v3_judge*` | `scripts/build_symptom_meta.py`, `app/services/hybrid.py`, `tests/56*` | chỉ file mới `tests/conftest.py`, `tests/test_*.py` |
| bắt buộc không sửa | còn lại | `pipeline.py`, `topic_filter.py`, `tests/51*`, `tests/52*`, `tests/test_*` | mọi file có sẵn |

Không ai trong ba người chạy sinh câu trả lời bằng LLM — việc đó chỉ chạy trên máy
chủ dự án, vì máy chỉ có một iGPU yếu (chạy song song đã từng làm hỏng 2 câu trong
bộ eval 50 câu).
