# Prompt soát vòng 3: bỏng, ngộ độc, đuối nước (bản tự chứa)

Dán cả khối dưới đây vào chat. Không cần đính kèm file.

```
Bạn là bác sĩ cấp cứu người Việt, đang soát nội dung sơ cứu cho một chatbot y tế
tiếng Việt. Bộ dấu hiệu cấp cứu đã qua ba vòng soát chung; lần này chỉ còn ba nhóm
dưới đây cần đối chiếu với **thực hành tại Việt Nam** vì hướng dẫn quốc tế và thực
hành trong nước khác nhau ở vài điểm.

YÊU CẦU QUAN TRỌNG

- KHÔNG viết lại toàn bộ file, KHÔNG xuất JSONL. Chỉ nêu đúng chỗ cần sửa.
- Mỗi ý sửa phải chỉ rõ: id nhóm, câu hiện tại (chép lại), câu thay thế đề xuất, và
  lý do ngắn.
- Mỗi nhóm tối đa 5 dòng lời khuyên, mỗi dòng một câu đầy đủ, dễ đọc trong lúc hoảng.
- Không đưa liều thuốc bằng số (mg, ml, viên, g/…). Nếu cần nói lượng, dùng cách nói
  định tính.
- Trong trường `mau` không dùng ký tự regex; chỉ cho phép "..." nghĩa là "cách nhau
  vài từ".
- Nếu một khuyến cáo chỉ đúng ở nước ngoài mà không phù hợp Việt Nam (thiếu thuốc,
  thiếu đơn vị hồi sức, thói quen dân gian), nói rõ và đề xuất cách viết phù hợp.

Trả lời đúng 3 phần:

PHẦN A — Nội dung cần sửa
Bảng: id | câu hiện tại | vấn đề | câu thay thế | nguồn (tên hướng dẫn + năm, hoặc
"kinh nghiệm thực hành").

PHẦN B — Mẫu câu cần thêm hoặc bớt
Bảng: id | thêm/bớt | cụm từ | lý do. Với mẫu dễ báo nhầm, nêu một câu ví dụ sẽ khớp sai.

PHẦN C — Phải có bác sĩ quyết
Những điểm mà bạn không chắc, hoặc cách làm tại cơ sở y tế địa phương khác nhau.

Nội dung ba nhóm hiện tại:

```json
[
{
  "id": "bong-nhiet",
  "nhom": "Bỏng nhiệt và bỏng hoá chất",
  "mau": [
    "bỏng nặng",
    "bỏng diện rộng",
    "bỏng nước sôi",
    "bị bỏng",
    "phỏng nước sôi",
    "bỏng lửa",
    "bỏng dầu",
    "bỏng hoá chất",
    "bỏng axit",
    "bỏng vôi"
  ],
  "loi_khuyen": [
    "- Gọi 115 nếu bỏng rộng, bỏng ở mặt, tay chân, vùng sinh dục hoặc nghi hít khói.",
    "- Làm mát ngay dưới vòi nước mát chảy nhẹ khoảng 20 phút; không dùng đá lạnh.",
    "- Tháo nhẫn và đồ chật trước khi sưng; không chọc bọng nước, không bôi kem hay mắm muối.",
    "- Che bằng gạc sạch hoặc màng bọc thực phẩm sạch; bỏng hoá chất thì rửa nhiều nước."
  ],
  "uu_tien": 31
},
{
  "id": "ngo-doc",
  "nhom": "Ngộ độc, quá liều",
  "uu_tien": 24,
  "mau": [
    "quá liều",
    "ngộ độc",
    "uống nhầm",
    "uống quá nhiều thuốc",
    "quá nhiều thuốc",
    "uống thuốc diệt chuột",
    "thuốc trừ sâu",
    "uống xăng",
    "uống dầu hoả",
    "uống acid",
    "uống thuốc ngủ",
    "khí than",
    "khí CO",
    "đốt than trong phòng",
    "nuốt pin",
    "nấm độc",
    "lá ngón"
  ],
  "khong_khop": [
    "ngộ độc thực phẩm",
    "ngộ độc thức ăn"
  ],
  "loi_khuyen": [
    "- Gọi 115, giữ lại vỏ thuốc, chai lọ và đơn thuốc để bác sĩ biết đã dùng gì.",
    "- Quá liều paracetamol có thể chưa có triệu chứng gì mà vẫn nguy hiểm: vẫn phải đi cấp cứu.",
    "- Nghi khí độc: mở cửa, đưa nạn nhân ra ngoài ngay; không bật lửa hay công tắc điện.",
    "- Hoá chất dính da hoặc mắt: cởi quần áo nhiễm và rửa nhiều nước liên tục 15 đến 20 phút.",
    "- Không tự gây nôn, nhất là khi đã uống xăng dầu hoặc chất tẩy ăn mòn.",
    "- Không tự trung hoà bằng giấm, sữa hay than hoạt khi chưa có hướng dẫn."
  ]
},
{
  "id": "duoi-nuoc",
  "nhom": "Đuối nước",
  "mau": [
    "đuối nước",
    "ngạt nước",
    "chết đuối",
    "sặc nước"
  ],
  "loi_khuyen": [
    "- Đưa nạn nhân lên bờ an toàn, gọi 115; không nhảy xuống nếu không biết bơi cứu hộ.",
    "- Không thở: thổi ngạt 5 lần ngay, rồi ép tim 30 lần và thổi 2 lần, lặp lại.",
    "- Không chờ nước trong bụng ra hết, không dốc ngược nạn nhân.",
    "- Tỉnh lại vẫn phải đến viện, vì nước vào phổi có thể gây khó thở muộn."
  ],
  "uu_tien": 30
}
]
```

Bối cảnh kỹ thuật, chỉ để hiểu, không cần trả lời: mỗi nhóm có `uu_tien` (nhỏ xét
trước), `mau` (cụm từ so khớp trên câu hỏi đã chuẩn hoá), `loi_khuyen` (hiện lên đầu
câu trả lời của chatbot), và tuỳ chọn `khong_khop` (khớp thì huỷ) / `kem_theo` (phải
khớp thêm mới tính).
```
