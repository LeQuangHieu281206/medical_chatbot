# Báo cáo hợp đồng dữ liệu

Sinh bởi `scripts/validate_data.py` (lenient).
Ngưỡng: xem `data/DATA_CONTRACT.md`.

## `data/processed/kb.jsonl` — 16961 dòng

| trạng thái | luật | mức | chi tiết |
|---|---|---|---|
| PASS | parse JSONL | hard | 16961 dòng hợp lệ |
| PASS | trường bắt buộc source, question, answer | hard | đủ |
| WARN | độ dài đáp án 100–2000 | soft | < 100 ký tự: 321, > 2000: 293 |
| WARN | 100% dòng có link nguồn | soft | 7973/16961 (47.0%) |
| PASS | không có câu hỏi trùng khít | hard | 0 dòng dư (0 nhóm) |
| WARN | không có câu hỏi gần trùng (Jaccard ≥ 0.70) | soft | 13 dòng dư (13 nhóm) — xem data/audit/duplicates.csv |
| WARN | mỗi chủ đề ≥ 400 câu | soft | 8 chủ đề mỏng: vaccine 84; dinh-duong 97; rhm 315; tam-than 315; tieu-duong 358; than-tiet-nieu 369; than-kinh 378; thai-san 399 |

## `data/processed/kb_drugs_25_full.jsonl` — 121 dòng

| trạng thái | luật | mức | chi tiết |
|---|---|---|---|
| PASS | parse JSONL | hard | 121 dòng hợp lệ |
| PASS | trường bắt buộc source, question, answer | hard | đủ |
| WARN | độ dài đáp án 100–2000 | soft | < 100 ký tự: 2, > 2000: 0 |
| PASS | 100% dòng có link nguồn | soft | 121/121 (100.0%) |
| PASS | không có câu hỏi trùng khít | hard | 0 dòng dư (0 nhóm) |
| WARN | ≥ 200 hoạt chất | soft | có 25 |
| WARN | mỗi hoạt chất đủ 5 khía cạnh | soft | 1 hoạt chất thiếu: atorvastatin(adr,caution,contraindication,interaction) |
| PASS | mỗi (hoạt chất, khía cạnh) chỉ 1 dòng | hard | đủ |
| PASS | facet thuộc 5 khía cạnh đã định | hard | đủ |

## `data/processed/eval.jsonl` — 2311 dòng

| trạng thái | luật | mức | chi tiết |
|---|---|---|---|
| PASS | parse JSONL | hard | 2311 dòng hợp lệ |
| PASS | trường bắt buộc source, question, answer | hard | đủ |
| WARN | độ dài đáp án 100–2000 | soft | < 100 ký tự: 38, > 2000: 38 |
| WARN | 100% dòng có link nguồn | soft | 2012/2311 (87.1%) |
| PASS | không có câu hỏi trùng khít | hard | 0 dòng dư (0 nhóm) |
| WARN | không có câu hỏi gần trùng (Jaccard ≥ 0.70) | soft | 2 dòng dư (2 nhóm) — xem data/audit/duplicates.csv |

## `data/processed/kb_chunked.jsonl` — 19827 dòng

| trạng thái | luật | mức | chi tiết |
|---|---|---|---|
| PASS | parse JSONL | hard | 19827 dòng hợp lệ |
| PASS | trường bắt buộc parent_id, question, text | hard | đủ |
| WARN | độ dài chunk 80–1200 | soft | quá ngắn: 276, quá dài: 0 |
| PASS | parent_id trỏ đúng dòng kb.jsonl | hard | 0 chunk trỏ sai (kb có 16961 dòng) |
| PASS | câu hỏi chunk khớp câu hỏi cha | hard | đủ |

## `data/processed/eval_noisy.jsonl` — 2000 dòng

| trạng thái | luật | mức | chi tiết |
|---|---|---|---|
| PASS | parse JSONL | hard | 2000 dòng hợp lệ |
| PASS | trường bắt buộc id, mode, original, noisy | hard | đủ |

## `data/processed/ner_train.jsonl` — 7000 dòng

| trạng thái | luật | mức | chi tiết |
|---|---|---|---|
| PASS | parse JSONL | hard | 7000 dòng hợp lệ |
| PASS | tokens và labels cùng độ dài | hard | 0 dòng lệch |
| PASS | nhãn nằm trong ner_labels.json | hard | đủ |

## `data/processed/ner_dev.jsonl` — 1000 dòng

| trạng thái | luật | mức | chi tiết |
|---|---|---|---|
| PASS | parse JSONL | hard | 1000 dòng hợp lệ |
| PASS | tokens và labels cùng độ dài | hard | 0 dòng lệch |
| PASS | nhãn nằm trong ner_labels.json | hard | đủ |

## `data/processed/ner_test.jsonl` — 1000 dòng

| trạng thái | luật | mức | chi tiết |
|---|---|---|---|
| PASS | parse JSONL | hard | 1000 dòng hợp lệ |
| PASS | tokens và labels cùng độ dài | hard | 0 dòng lệch |
| PASS | nhãn nằm trong ner_labels.json | hard | đủ |

