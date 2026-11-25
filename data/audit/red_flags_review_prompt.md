# Prompt nhờ AI khác soát bộ red flag

Dùng cho Claude / ChatGPT (bản có đọc file). Đính kèm `data/sources/red_flags.jsonl`.
Kết quả trả về dán vào `data/sources/red_flags.jsonl` rồi chạy:

```
.venv/bin/python scripts/validate_data.py data/sources/red_flags.jsonl --strict
.venv/bin/python tests/54_test_red_flags.py -v
```

---

## Prompt chính (soát + viết lại lời khuyên sơ cứu)

```
Bạn là bác sĩ cấp cứu người Việt, đồng thời là biên tập viên y khoa cho nội dung
phổ thông. Tôi đang xây một chatbot y tế tiếng Việt chạy local, trả lời cho người
dân không có chuyên môn.

File đính kèm `red_flags.jsonl` là bộ nhận diện dấu hiệu cấp cứu: mỗi dòng là một
nhóm (id, nhom, uu_tien, mau[], loi_khuyen[]).
  - `mau`: các cụm từ, so khớp trên câu hỏi đã chuẩn hoá (đã khôi phục dấu, đã mở
    rộng teencode/viết tắt). Đây là chuỗi thường, KHÔNG phải regex.
  - `loi_khuyen`: các dòng hiện lên ĐẦU câu trả lời, trước cả phần trả lời của mô
    hình. Nhỏ hơn `uu_tien` thì xét trước.
  - `khong_khop` (tuỳ chọn): khớp mẫu này thì huỷ kết quả — dùng để chặn báo nhầm.
    `kem_theo` (tuỳ chọn): phải khớp thêm mẫu này mới tính — dùng khi cần đủ ngữ
    cảnh. Trong mọi trường mẫu, `...` nghĩa là "cách nhau vài từ".
  - GIỮ NGUYÊN hai trường tuỳ chọn đó nếu nhóm đã có; đừng xoá.

Nhiệm vụ: soát lại toàn bộ và viết lại phần `loi_khuyen` cho an toàn, đúng, và dễ
làm theo, đồng thời bổ sung `mau` còn thiếu.

Ràng buộc bắt buộc cho `loi_khuyen`:
  1. Không nêu liều thuốc bằng số (không "500mg", "2 viên", "10ml"). Nói "theo
     đúng liều trên nhãn hoặc theo chỉ định của bác sĩ".
  2. Không nêu tên biệt dược; chỉ tên hoạt chất nếu thật cần.
  3. Tối đa 4 gạch đầu dòng, mỗi dòng tối đa 25 từ, bắt đầu bằng động từ mệnh
     lệnh ("Gọi…", "Đặt…", "Không…").
  4. Không chẩn đoán chắc chắn ("đây là nhồi máu cơ tim"); dùng "nghi", "có thể".
  5. Không hứa kết quả ("sẽ khỏi", "không sao"), không trấn an quá mức.
  6. Không đặt người bệnh vào nguy hiểm: không gây nôn khi nghi uống xăng dầu/chất
     ăn mòn, không nhét vật vào miệng khi co giật, không chườm đá lạnh lên bỏng,
     không tự dùng thuốc giảm đau khi đau bụng cấp, không khuyên tự lái xe khi
     nghi nhồi máu cơ tim.
  7. Luôn có ít nhất một dòng nói rõ gọi 115 hoặc đến cơ sở y tế.
  8. Trung tính về giới, dễ hiểu với người lớn tuổi, câu ngắn.

Với `mau`, bổ sung cách nói thực tế của người Việt: khẩu ngữ, tiếng lóng, câu không
dấu, viết tắt hay gặp ("tai biến", "đứng tim", "sốc thuốc", "ngộp thở"…). Không
thêm cụm quá chung chung dễ báo nhầm (ví dụ "mệt", "đau", "sốt").

Hãy trả lời theo đúng 4 phần:

PHẦN 1 — Lỗi và rủi ro trong bản hiện tại
Bảng: id | mức độ (nguy hiểm / sai y khoa / thiếu / chỉ là câu chữ) | vấn đề | vì sao.

PHẦN 2 — Nhóm còn thiếu
Liệt kê tối đa 5 nhóm cấp cứu hay gặp ở Việt Nam mà file chưa có, kèm mẫu câu và
lời khuyên ngắn. Nếu không thiếu thì nói rõ là không thiếu.

PHẦN 3 — File JSONL hoàn chỉnh
Xuất lại TOÀN BỘ file, mỗi dòng một JSON object, giữ nguyên đúng schema và giữ
nguyên `id` cũ (id là khoá ổn định của test, đổi sẽ hỏng). Thêm nhóm mới thì đặt
id dạng không dấu, gạch nối. `uu_tien` phải là số nguyên duy nhất, và dấu hiệu
đặc hiệu phải có số nhỏ hơn dấu hiệu chung (ví dụ nghi nhiễm toan ceton trước
"khó thở"). Trong `loi_khuyen`, mỗi dòng bắt đầu bằng "- ".

PHẦN 4 — Cần bác sĩ Việt Nam duyệt lại
Những câu nào bạn không chắc, chỗ nào phác đồ Việt Nam khác hướng dẫn quốc tế.

Nguồn: khi một lời khuyên dựa trên hướng dẫn cụ thể, ghi tên hướng dẫn và năm ngay
sau dòng đó trong PHẦN 1 hoặc PHẦN 4 (ví dụ "AHA/ASA 2019", "Bộ Y tế VN"). Không
bịa nguồn: nếu không chắc thì ghi "không nêu nguồn".
```

---

## Prompt phụ (chỉ soát, không viết lại)

Dùng khi muốn giữ nguyên nội dung hiện tại và chỉ cần bắt lỗi:

```
Đính kèm `red_flags.jsonl` (bộ dấu hiệu cấp cứu của một chatbot y tế tiếng Việt
cho người không có chuyên môn). Chỉ soát, KHÔNG viết lại toàn bộ.

Với mỗi nhóm, nói rõ:
  1. Có lời khuyên nào sai y khoa hoặc có thể gây hại không?
  2. Có thiếu bước sơ cứu quan trọng nào không (theo hướng dẫn sơ cứu phổ thông)?
  3. `mau` có cụm nào dễ khớp nhầm câu bệnh thường không? Nêu ví dụ câu sẽ bị
     khớp nhầm.
  4. Câu chữ có chỗ nào người lớn tuổi đọc không hiểu, hoặc quá dài để đọc khi
     đang hoảng không?

Xuất bảng: id | mức độ | vấn đề | sửa đề xuất | nguồn (tên + năm, hoặc "không nêu nguồn").
Cuối cùng: 3 thay đổi quan trọng nhất nên làm trước.
```

---

## Sau khi có kết quả

Cách gọn nhất: lưu nguyên câu trả lời của AI vào một file, ví dụ
`data/audit/red_flags_answer.md` (dán cả bài, không cần tách), rồi:

```
.venv/bin/python scripts/merge_red_flags.py data/audit/red_flags_answer.md
```

Script tự tách khối JSONL, in khác biệt từng nhóm (mẫu thêm/bỏ, lời khuyên đổi),
cảnh báo liều thuốc và chạy `validate_data.py --strict`. Đọc xong, ưng thì ghi đè:

```
.venv/bin/python scripts/merge_red_flags.py data/audit/red_flags_answer.md --apply
.venv/bin/python tests/54_test_red_flags.py -v
```

`--apply` tự lưu bản cũ vào `data/audit/backup/red_flags.jsonl`.

Cách thủ công (nếu không dùng script): dán PHẦN 3 đè lên `data/sources/red_flags.jsonl`
rồi chạy 2 lệnh ở đầu file. `validate_data.py` sẽ chặn nếu có liều thuốc trong lời
   khuyên, thiếu nhóm, hay id trùng.
3. `tests/54_test_red_flags.py -v` sẽ chỉ ra câu mẫu nào không còn khớp — thường là
   do AI đổi `mau` quá tay.
4. So lại số câu bị cảnh báo trên dữ liệu thật để biết có báo nhầm nhiều hơn không:

```
.venv/bin/python - <<'PY'
import json, sys; sys.path.insert(0, '.')
from app.services import red_flags as R
for f in ("data/processed/eval.jsonl", "data/processed/kb.jsonl"):
    qs = [json.loads(l)["question"] for l in open(f)]
    print(f, sum(1 for q in qs if R.match(q)), "/", len(qs))
PY
```

Mốc hiện tại: `eval.jsonl` 144/2311, `kb.jsonl` 1151/16961.

5. Nội dung cuối vẫn phải có người có chuyên môn ở Việt Nam duyệt trước khi dùng
   cho người bệnh thật. AI soát giúp bắt lỗi, không thay được bước duyệt đó.
