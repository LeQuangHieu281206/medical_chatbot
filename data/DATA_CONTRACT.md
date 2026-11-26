# Hợp đồng dữ liệu

Mọi file trong `data/processed/` phải qua cổng `scripts/validate_data.py` trước khi
được nạp vào ChromaDB. File này ghi lại **luật nào, ngưỡng bao nhiêu, vì sao** và
**số đo hiện tại** để biết dữ liệu mới làm tốt lên hay tệ đi.

```bash
.venv/bin/python scripts/validate_data.py                     # kiểm tra tất cả
.venv/bin/python scripts/validate_data.py --report data/audit/contract_report.md
.venv/bin/python scripts/validate_data.py --strict data/processed/kb_<mảng>.jsonl
```

- `hard`: sai thì exit code 1, **không được nạp**.
- `soft`: chỉ cảnh báo. Chạy `--strict` khi duyệt **dữ liệu mới thêm** (dữ liệu mới
  phải đạt cả soft, dữ liệu cũ được miễn).

## 1. Schema

`kb.jsonl`, `eval.jsonl`, `kb_drugs_*_full.jsonl`:

| trường | kiểu | ghi chú |
|---|---|---|
| `source` | str | tên nguồn, khớp cột `source` trong báo cáo |
| `question` | str | câu hỏi đã bỏ lời chào, không rỗng |
| `answer` | str | đáp án, 100–2000 ký tự |
| `link` | str | URL nguồn. Rỗng = không truy vết được. Luật **soft** vì dữ liệu cũ thiếu |
| `facet` | str | chỉ file thuốc: `indication`, `contraindication`, `caution`, `adr`, `interaction` |

`kb_chunked.jsonl`: `parent_id` (int, trỏ đúng dòng `kb.jsonl`), `source`, `link`,
`question`, `section`, `text`.

`ner_*.jsonl`: `tokens[]` và `labels[]` cùng độ dài, nhãn thuộc `ner_labels.json`.

`eval_noisy.jsonl`: `id`, `mode`, `original`, `noisy`.

`data/sources/red_flags.jsonl` — bộ dấu hiệu cấp cứu (33 nhóm):

| trường | kiểu | ghi chú |
|---|---|---|
| `id` | str | khoá duy nhất, ví dụ `dot-quy` |
| `nhom` | str | tên hiển thị trong khối cảnh báo |
| `uu_tien` | int | nhỏ hơn xét trước; dấu hiệu đặc hiệu phải đứng trước dấu hiệu chung |
| `mau` | str[] | ≥ 3 mẫu câu, so khớp trên **câu đã chuẩn hoá**; chuỗi thường, không regex |
| `loi_khuyen` | str[] | các dòng sơ cứu; **không chứa liều thuốc** |
| `khong_khop` | str[]? | khớp mẫu này thì **huỷ** kết quả (chặn báo nhầm: "ngừng thở khi ngủ", "ngộ độc thực phẩm") |
| `kem_theo` | str[]? | phải khớp thêm mẫu này mới tính (buộc đủ ngữ cảnh: "chảy máu cam" cần có "sốt") |

Trong `mau`/`khong_khop`/`kem_theo`, `...` nghĩa là "cách nhau vài từ"
(`mang thai ... ra máu`). Ngoài `...` không dùng ký tự regex nào khác.

## 2. Luật và ngưỡng

| # | Luật | Mức | Ngưỡng | Vì sao ngưỡng này |
|---|---|---|---|---|
| R1 | Parse JSONL | hard | 0 dòng lỗi | Dòng hỏng làm ingest chết giữa đường |
| R2 | Trường bắt buộc không rỗng | hard | 0 dòng thiếu | `pipeline._qa_text` và ingest đọc trực tiếp |
| R3 | Độ dài đáp án | soft | 100–2.000 ký tự | < 100 thì không trả lời được gì (p1 hiện tại 74); > 2.000 thì `MAX_QA_CHARS=350` cắt gần hết |
| R4 | 100% có `link` | soft | 100% | Không có nguồn thì UI không hiển thị được, và không kiểm chứng được nội dung y tế |
| R5 | Không trùng khít câu hỏi | hard | 0 | Trùng khít chắc chắn là lỗi gộp dữ liệu, không phải khác biệt ngữ nghĩa |
| R6 | Không gần trùng (Jaccard ≥ 0,70) | soft | 0 | Gần trùng làm retrieval trả 3 bản sao của cùng một câu |
| R7 | Mỗi chủ đề ≥ 400 câu | soft | 400 | Dưới 400 thì retrieval gần như không bao giờ chạm tới chủ đề đó (xem `app/services/topic_taxonomy.py`) |
| R8 | ≥ 200 hoạt chất | soft | 200 | Dưới ngưỡng này câu hỏi về thuốc bị `DOSE_REPLY` chặn thay vì trả lời |
| R9 | Mỗi hoạt chất đủ 5 khía cạnh | soft | 5/5 | Trả lời "tương tác" mà thiếu `contraindication` là nguy hiểm |
| R10 | Mỗi (hoạt chất, khía cạnh) chỉ 1 dòng | hard | 0 | Câu hỏi theo mẫu nên gần trùng là giả; trùng theo cặp mới là lỗi |
| R11 | `facet` thuộc 5 khía cạnh | hard | 0 facet lạ | Facet lạ không được pipeline nào đọc tới |
| R12 | Độ dài chunk | soft | 80–1.200 ký tự | ~512 token của `multilingual-e5-small` |
| R13 | `parent_id` trỏ đúng `kb.jsonl` | hard | 0 sai | Chunk mồ côi làm parent expansion (`tests/20`) trả rỗng |
| R13b | Câu hỏi chunk khớp câu hỏi cha | hard | 0 lệch | Xoá/gộp dòng trong `kb.jsonl` làm lệch chỉ số của mọi dòng sau — lỗi im lặng, phải chạy lại `scripts/rechunk_qa.py` |
| R14 | `tokens`/`labels` cùng độ dài | hard | 0 lệch | Trainer XLM-R crash ngay batch đầu |
| R15 | Nhãn NER thuộc `ner_labels.json` | hard | 0 nhãn lạ | Nhãn lạ bị map thành `-100`, mất tín hiệu huấn luyện |

## 3. Số đo hiện tại

Đo ngày 2025-11-25 bằng `.venv/bin/python scripts/validate_data.py`, sau hai thay đổi:
gộp câu trùng khít (`scripts/dedupe_kb.py`) và mở rộng KB thuốc từ 25 hoạt chất lên
441 hoạt chất (`scripts/build_drug_index.py` → `scripts/build_drug_qa.py`).

| File | Dòng | Trạng thái | Vi phạm |
|---|---|---|---|
| `kb.jsonl` | 16.961 | đạt hard | R3: 321 đáp án < 100, 293 > 2.000 · R4: 47,0% có link · R6: 12 nhóm gần trùng · R7: 8 chủ đề mỏng |
| `kb_drugs_25_full.jsonl` | 121 | đạt hard | R8: 25/200 · R9: `atorvastatin` thiếu 4 khía cạnh · R3: 2 đáp án < 100 |
| `kb_drugs_full.jsonl` | 2.205 | **đạt cả --strict** | không vi phạm: 441 hoạt chất × 5 khía cạnh, 100% có link |
| `kb_merged.jsonl` | 19.166 | đạt hard | như `kb.jsonl` + thuốc (R4: 53,1% có link) |
| `kb_chunked.jsonl` | 19.827 | đạt hard | R12: 276 chunk < 80 ký tự |
| `kb_merged_chunked.jsonl` | 22.032 | đạt hard | R12: 276 chunk < 80 ký tự |
| `eval.jsonl` | 2.311 | đạt hard | R4: 87,1% có link |
| `eval_noisy.jsonl` | 2.000 | đạt | — |
| `ner_train/dev/test.jsonl` | 7.000 / 1.000 / 1.000 | đạt | — |

Chủ đề mỏng (R7): `vaccine` 84, `dinh-duong` 97, `rhm` 315, `tam-than` 315,
`tieu-duong` 358, `than-tiet-nieu` 369, `than-kinh` 378, `thai-san` 399.
`ho-hap` đang chiếm 45,7% toàn bộ KB.

12 nhóm gần trùng (R6) chưa gộp: xem `scripts/dedupe_kb.py --near` để lấy kế hoạch,
nhưng phải duyệt tay vì có cặp chỉ khác một từ mà nghĩa khác nhau.

Nguồn thuốc: 700 slug chuyên luận trên mirror Dược thư (Bạch Mai) → 542 trang là
chuyên luận thật → 477 đủ 5 khía cạnh → 441 hoạt chất cho ra đủ 5 đáp án ≥ 100 ký tự.
Danh mục ở `data/sources/duocthu/index.jsonl`, HTML gốc cache ở
`data/sources/duocthu/raw/` (67 MB, build lại không cần mạng).

### 3.1 Trạng thái vector DB

`medical_kb` = `kb_merged.jsonl` (19.166 document), khớp đúng từng dòng với file.
Thuốc được thêm vào bằng `ingest_kb.py --append` (upsert theo id `kb_drugs_full-<i>`),
không xoá collection, nên lần nạp chỉ mất ~2 phút thay vì ~80 phút embed lại toàn bộ.

| Collection | Document | Dùng bởi |
|---|---|---|
| `medical_kb_v3` | 25.197 | **mặc định hiện tại**: `TopicFilter` + truy hồi QA của pipeline |
| `medical_kb` | 19.166 | bản trước khi thêm Vinmec, giữ để quay lại (`KB_COLLECTION=medical_kb`) |
| `medical_kb_vimedaqa` | 17.952 | truy hồi bài viết y khoa (không đổi) |
| `medical_kb_v2` | 19.830 | thí nghiệm tách chunk, pipeline **không** đọc |

Đổi collection mặc định không cần sửa code: `KB_COLLECTION=medical_kb_v3` (mặc định)
hoặc `KB_COLLECTION=medical_kb` để quay lại.

Đo lại sau khi nạp (cùng 500 câu eval, cùng model embedding):

| Collection | Document | Recall@1 | Recall@3 |
|---|---|---|---|
| `medical_kb` | 19.166 | 10,2% | 11,6% |
| `medical_kb_v3` | 25.197 | 10,4% | 12,2% |

Giới hạn của phép đo: recall tính bằng "đáp án chuẩn nằm trong tài liệu truy hồi",
nên nội dung đúng nghĩa nhưng diễn đạt khác (Vinmec) không được tính. Vì vậy con số
trên là **sàn**, không phải toàn bộ lợi ích. Cần bộ eval riêng cho vaccine/dinh dưỡng
để đo đúng. Khoảng cách topic filter của 10 câu
ngoài chủ đề không đổi (1/10 lọt ngưỡng PASS cả trước và sau).

Để nạp lại từ đầu (khi đổi model embedding hoặc đổi cách chia đoạn):

```bash
cp -r app/db/chroma_db app/db/chroma_db.bak
.venv/bin/python app/services/ingest_kb.py --kb data/processed/kb_merged.jsonl
```

### 3.2 Mảng vaccine và dinh dưỡng (nguồn Vinmec)

Hai chủ đề này mỏng nhất trong `kb.jsonl` (85 và 99 câu) trong khi `ho-hap` chiếm
45,7%. Hai bộ dữ liệu gốc đã dùng hết, nên phải lấy nguồn ngoài:

| Hạng mục | Giá trị |
|---|---|
| Nguồn | `https://www.vinmec.com/vie/bai-viet/…` (bệnh viện Vinmec) |
| Điều kiện đọc | `robots.txt` cho phép toàn bộ trừ trang đăng nhập/quản trị |
| Cách lấy | `scripts/build_vinmec_qa.py`: sitemap → lọc slug theo chủ đề → tải bài (cache `data/sources/vinmec/html/`) |
| Câu hỏi | lấy từ `<h1>` của bài; đáp án là thân bài đã bỏ khung trang |
| Số dòng | 6.031 dòng dùng được (1.986 + 5.975 lượt tải; phần còn lại trùng hoặc lệch chủ đề) |
| Truy vết | 100% dòng có `link`, `source = "Vinmec"` |

**Giới hạn pháp lý:** đây là nội dung của một bệnh viện tư nhân, không phải văn bản
nhà nước như Dược thư. Dùng cho đồ án/demo học tập thì giữ nguyên `link` và ghi tên
nguồn ở UI; dùng thương mại phải xin phép. Khi có nguồn nhà nước cùng nội dung
(Viện Dinh dưỡng, Chương trình TCMR), thay dần bằng cách lọc `source`.

Lệnh dựng lại (cần mạng, ~10 phút cho 8.000 bài):

```bash
.venv/bin/python scripts/build_vinmec_qa.py --per-topic 1000 \
    --out data/processed/kb_vinmec.jsonl
.venv/bin/python scripts/build_vinmec_qa.py --strong --per-topic 3000 \
    --out data/processed/kb_vinmec_2.jsonl --purge-cache
.venv/bin/python scripts/build_kb_merged.py \
    --extra data/processed/kb_drugs_full.jsonl \
    --extra data/processed/kb_vinmec.jsonl \
    --extra data/processed/kb_vinmec_2.jsonl \
    --exclude data/processed/eval.jsonl \
    --out data/processed/kb_merged_v3.jsonl
```

`--exclude eval.jsonl` là bắt buộc: câu hỏi held-out không được lọt vào KB, nếu không
Recall sẽ đo trên chính dữ liệu đã học.

### 3.3 Thước đo truy hồi — dùng cái nào

`scripts/eval_kb_recall.py` tính "đáp án chuẩn nằm nguyên văn trong tài liệu truy hồi".
Với dữ liệu ViHealthQA, mỗi câu có một đáp án dài riêng nên phép đo này chỉ đạt ~12%
**kể cả khi truy hồi đúng chủ đề** — nó đo trùng chữ, không đo đúng ý. Trần của nó
chỉ 13,0% (đo ở top-20), nên đừng dùng để kết luận truy hồi tốt hay kém.

Thước đo dùng để ra quyết định: `scripts/eval_retrieval_semantic.py` — so cosine giữa
đáp án chuẩn và đáp án được truy hồi (ngưỡng 0,88; cặp ngẫu nhiên trong KB chỉ đạt
0,834 trung bình, p90 = 0,864, nên ngưỡng này không phải đoán mò).

| Thước đo | `medical_kb` | `medical_kb_v3` |
|---|---|---|
| Trùng chữ, Recall@3 | 11,6% | 12,2% |
| **Đúng ý @1** | **73,7%** | 73,0% |
| **Đúng ý @3** | **87,3%** | 86,3% |

Kết luận: truy hồi **không** phải nút thắt (86% ở top-3), và bản v3 không tốt hơn bản
cũ về truy hồi — nó chỉ tăng độ phủ chủ đề và tỉ lệ có link nguồn.

Hai hướng đã thử và **không tăng** recall (ghi lại để khỏi làm lại):

- `app/services/rerank.py` — xếp lại top-20 bằng từ vựng rồi chọn top-3. Quét toàn bộ
  tổ hợp trọng số trên 500 câu: tốt nhất đúng bằng baseline 11,6%, không hơn.
- TF-IDF (1–2 gram) fuse với dense theo RRF: 11,6% → 11,4% (giảm nhẹ).

Vì truy hồi đã ổn, 26% câu trả lời có thông tin bịa là lỗi ở bước **viết câu trả lời**.
`app/services/grounding.py` đo tỉ lệ token của từng câu có trong ngữ cảnh: nhóm bịa
0,41 so với nhóm không bịa 0,62 — phân biệt được nhưng chưa đủ chắc để tự động cắt
câu (43% câu đúng cũng bị chấm dưới 0,6). Muốn dùng làm cổng chặn phải hiệu chỉnh
lại sau khi chấm lại 50 câu trên pipeline hiện tại.

## 4. Quy trình thêm một mảng dữ liệu

1. **Raw bất biến** — `data/sources/<mảng>/`, mỗi dòng có `source`, `url`, `license`,
   `crawled_at`. Không sửa tay file raw.
2. **Build** — `scripts/build_<mảng>.py` đọc raw, ghi `data/processed/<mảng>.jsonl`
   đúng schema ở mục 1. Mẫu có sẵn: `scripts/build_drug_qa.py`.
3. **Validate** — `--strict` trên file mới. Còn FAIL thì sửa, không nạp.
4. **Audit** — `tests/40_data_audit.py` cập nhật `data/audit/*.csv` để so phân bố
   chủ đề và trùng lặp với lần trước.
5. **Gộp trùng** — `scripts/dedupe_kb.py <file> --apply`. Sửa `kb.jsonl` thì bắt
   buộc chạy lại `scripts/rechunk_qa.py`, không thì R13b báo lệch hàng loạt.
6. **Ingest vào collection mới** — `app/services/ingest_kb_v2.py` (hoặc `_v3`), không
   xoá collection đang chạy, để còn so sánh.
7. **Eval trước/sau** — `tests/17_eval_retrieval.py`, `tests/26_run_eval.py`. Chỉ đổi
   collection mặc định khi số liệu tốt hơn.

### 4.1 Bộ dấu hiệu cấp cứu

Nội dung nằm ở `data/sources/red_flags.jsonl`, code đọc ở `app/services/red_flags.py`
(`match`, `prefix`), `pipeline.py` không còn hard-code danh sách này. Kiểm bằng:

```
.venv/bin/python tests/54_test_red_flags.py -v   # recall + báo nhầm + luật liều
.venv/bin/python scripts/validate_data.py data/sources/red_flags.jsonl --strict
```

Hiện tại: 33 nhóm, 286 mẫu, recall 56/56 câu mẫu, báo nhầm 0/49 câu bệnh thường (trong đó
có bộ câu bẫy "có từ khoá nhưng không nguy hiểm"). Trên dữ liệu thật, cảnh báo xuất hiện ở
158/2.311 câu `eval.jsonl` và 1.256/16.961 câu `kb.jsonl` (bộ regex cũ: 89 và 712).

Vòng soát thứ hai (đối chiếu AHA, ERC, WHO, hướng dẫn Bộ Y tế) đã sửa 10 điểm nội dung:
làm mát bằng nước lạnh/chườm đá bọc khăn thay vì cấm đá; aspirin chỉ dùng khi tổng đài 115
hướng dẫn; thêm dấu hiệu không điển hình của nhồi máu; nêu ý chính ép tim trẻ em và thổi
ngạt khi đuối nước; bất động chi + băng ép vừa phải khi rắn cắn; tách bỏng / điện giật /
đuối nước thành ba nhóm; thêm quá liều paracetamol không triệu chứng và rửa hoá chất dính
da, mắt; hóc có bất tỉnh, người mang thai; mũ bảo hiểm có ngoại lệ khi cần mở đường thở.
Thêm 10 nhóm: ngất, ý định làm hại người khác, thuyên tắc phổi, viêm màng não, trẻ dưới 3
tháng sốt, mất nước nặng, chấn thương mắt, gãy xương/vết thương hở, bỏng nhiệt, điện giật,
đuối nước.

Hai thay đổi về cách khớp:

- `kem_theo` nay kiểm trên phần câu **còn lại** sau khi bỏ đoạn đã khớp. Trước đây
  "sốt xuất huyết là bệnh gì" cũng bị coi là cấp cứu vì cụm "sốt xuất huyết" tự chứa chữ "sốt".
- Câu khớp nhiều nhóm thì hiện đủ nhóm ưu tiên cao nhất và chèn thêm dòng hành động của
  nhóm nguy hiểm tức thì khác (ngừng tuần hoàn, hóc, phản vệ) cùng một nhóm còn lại. Ví dụ
  "uống cả vỉ thuốc ngủ, bất tỉnh, không thở" hiện ép tim và cả lời khuyên giữ lại vỏ thuốc.

Số hotline 1900 1267 đã bỏ khỏi nhóm tự hại vì chưa xác minh lại được; hiện chỉ còn 115,
096 306 1414 (đường dây Ngày mai) và 111 (trẻ em) — hai số sau đã được người soát xác nhận
còn đúng.

Ba chỗ đã chốt câu chữ sau khi người soát duyệt:

- **Aspirin trong nhồi máu cơ tim**: không tự cho uống. Gọi 115 trước, nói rõ dị ứng và tiền
  sử chảy máu; chỉ cho nhai aspirin khi tổng đài 115 hoặc nhân viên y tế hướng dẫn, hoặc khi
  người bệnh đã có đơn sẵn cho tình huống này. Lý do: liều nạp chỉ có lợi khi chắc là nhồi
  máu, còn có thể sai trong bóc tách động mạch chủ, xuất huyết tiêu hoá, hoặc đang dùng thuốc
  chống đông.
- **Băng ép khi rắn cắn**: tách hẳn hai nhóm vì cách sơ cứu ngược nhau.
  `ran-can` (không rõ loài, nghi nọc thần kinh): băng thun quấn từ ngọn chi lên gốc chi, vừa
  đủ chặt để vẫn bắt được mạch, kèm nẹp bất động; tuyệt đối không garô. `ran-luc`: **không**
  băng ép, vì nọc gây sưng nề, hoại tử tại chỗ và rối loạn đông máu — chỉ bất động, để chi
  ngang hoặc thấp hơn tim và chuyển đi cấp cứu nhanh.
- **Ngất**: nằm ngửa nơi thoáng, nâng nhẹ chân, nới đồ; kiểm tra phản ứng và nhịp thở,
  nghiêng đầu nếu nôn; không thở thì gọi 115 và ép tim; chưa tỉnh hẳn thì không cho ăn uống,
  không châm kim cạo gió; ngất kéo dài, chấn thương khi ngã, đau ngực, khó thở, co giật hoặc
  ngất khi gắng sức thì gọi 115.

Đánh đổi đã biết: câu hỏi *thông tin* về bệnh mạn tính ("điều trị động kinh thế
nào") vẫn nhận khối cảnh báo, nhưng câu mở đầu là điều kiện "Nếu đây là tình huống
khẩn cấp đang xảy ra..." nên không gây hiểu sai. Cố ý chọn thà cảnh báo thừa còn
hơn bỏ sót cơn cấp.

Lời khuyên sơ cứu là nội dung tự soạn theo hướng dẫn sơ cứu thông thường, **chưa
qua bác sĩ duyệt**. Trước khi dùng cho người bệnh thật phải có người có chuyên môn
đọc lại, đặc biệt các nhóm `tu-hai`, `soc-phan-ve`, `ngo-doc`.

## 5. Ghi chú

- Danh sách nhãn chuyên khoa nằm ở `app/services/topic_taxonomy.py` (một nguồn duy
  nhất, `tests/40_data_audit.py` và validator cùng import). Thêm chủ đề mới thì sửa
  ở đó.
- Hàm so trùng nằm ở `app/services/data_quality.py`.
- Ngưỡng trong file này và trong `scripts/validate_data.py` phải sửa cùng lúc.
