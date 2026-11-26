# Prompt soát vòng 4: chấn thương, chảy máu và 5 nhóm chưa soát

Dán cả khối dưới đây vào chat. Không cần đính kèm file.

```
Bạn là bác sĩ cấp cứu người Việt, soát nội dung sơ cứu cho một chatbot y tế tiếng Việt.
Bộ 33 nhóm dấu hiệu cấp cứu đã qua bốn vòng soát; tám nhóm dưới đây là những nhóm
**chưa được soát lần nào** hoặc mới chỉ được ghi "ổn" qua loa, nên cần đọc kỹ.

YÊU CẦU QUAN TRỌNG

- KHÔNG viết lại toàn bộ file, KHÔNG xuất JSONL. Chỉ nêu đúng chỗ cần sửa.
- Mỗi ý sửa: id nhóm, câu hiện tại (chép lại), câu thay thế đề xuất, lý do ngắn, nguồn.
- Mỗi nhóm tối đa 5 dòng lời khuyên, mỗi dòng một câu đầy đủ, đọc được trong lúc hoảng.
- Không đưa liều thuốc bằng số. Nếu cần nói lượng, dùng cách nói định tính.
- Trong trường `mau` không dùng regex; chỉ cho phép "..." nghĩa là "cách nhau vài từ".
- Đối chiếu thực hành cấp cứu ngoại viện tại Việt Nam (Bộ Y tế, bệnh viện tuyến tỉnh,
  trạm y tế xã) chứ không chỉ hướng dẫn quốc tế.

Trả lời đúng 3 phần:

PHẦN A — Nội dung cần sửa: bảng id | câu hiện tại | vấn đề | câu thay thế | nguồn
PHẦN B — Mẫu câu thêm/bớt: bảng id | thêm/bớt | cụm từ | lý do. Với mẫu dễ báo nhầm,
nêu một câu ví dụ sẽ khớp sai.
PHẦN C — Phải có bác sĩ quyết: điểm chưa chắc hoặc nơi làm khác nhau.

Nội dung tám nhóm hiện tại:

```json
[
{
  "id": "chan-thuong-dau",
  "nhom": "Chấn thương đầu, cột sống",
  "uu_tien": 25,
  "mau": [
    "đập đầu",
    "chấn thương đầu",
    "ngã từ trên cao",
    "tai nạn xe",
    "chấn thương cột sống",
    "không cử động được tay chân",
    "nôn sau khi đập đầu",
    "chảy máu tai sau ngã"
  ],
  "loi_khuyen": [
    "- Gọi 115; không tự di chuyển nạn nhân, không nắn cổ hay cột sống.",
    "- Không tháo mũ bảo hiểm, trừ khi cần mở đường thở hoặc ép tim.",
    "- Vết thương chảy máu thì ấn gạc sạch liên tục, không ấn mạnh nếu nghi lún sọ.",
    "- Theo dõi ý thức, nôn, đau đầu tăng dần và báo cho nhân viên y tế."
  ]
},
{
  "id": "gay-xuong-vet-thuong",
  "nhom": "Gãy xương, vết thương hở",
  "mau": [
    "gãy xương hở",
    "gãy xương ... lộ",
    "lộ xương",
    "xương lộ ra",
    "gãy chân ... không đứng được",
    "gãy tay ... biến dạng",
    "vết thương ... chảy máu nhiều",
    "vết thương sâu ... cần khâu",
    "đứt tay ... chảy máu nhiều",
    "vết thương do đinh ... chảy máu",
    "ngã gãy",
    "tai nạn gãy",
    "gãy ... sưng",
    "gãy ... biến dạng"
  ],
  "loi_khuyen": [
    "- Gọi 115 nếu chi biến dạng, lộ xương, chảy máu nhiều hoặc nghi gãy cổ, gãy cột sống.",
    "- Bất động chi ở tư thế đang có bằng nẹp hoặc vật cứng, không tự nắn lại.",
    "- Vết thương chảy máu: ấn trực tiếp bằng gạc sạch liên tục, rửa vết thương dưới nước sạch.",
    "- Không rút vật đang cắm sâu, không đắp lá hay bôi thuốc vào vết thương hở."
  ],
  "uu_tien": 33,
  "khong_khop": [
    "sau phẫu thuật",
    "sau mổ",
    "hậu phẫu",
    "thuốc bôi",
    "sau khi mổ"
  ]
},
{
  "id": "chay-mau",
  "nhom": "Chảy máu, xuất huyết tiêu hoá",
  "uu_tien": 26,
  "mau": [
    "chảy máu nhiều",
    "chảy máu không cầm",
    "nôn ra máu",
    "ói ra máu",
    "nôn bã cà phê",
    "đi ngoài phân đen",
    "máu chảy thành tia",
    "đi cầu ra máu tươi",
    "đi ngoài phân đen",
    "phân đen như bã cà phê"
  ],
  "loi_khuyen": [
    "- Gọi 115 hoặc đến cấp cứu ngay.",
    "- Vết thương chảy máu: ấn trực tiếp bằng gạc sạch liên tục, không tháo ra xem.",
    "- Nôn ra máu hoặc phân đen: không ăn uống, nằm nghiêng; gọi 115 khi chóng mặt, vã mồ hôi.",
    "- Không tự dùng aspirin hay ibuprofen khi đang chảy máu."
  ]
},
{
  "id": "viem-mang-nao",
  "nhom": "Nghi viêm màng não",
  "mau": [
    "viêm màng não",
    "cứng cổ",
    "sợ ánh sáng",
    "ban xuất huyết",
    "sốt ... cứng cổ",
    "đau đầu ... nôn ... cứng cổ"
  ],
  "loi_khuyen": [
    "- Đến cấp cứu ngay hoặc gọi 115: viêm màng não có thể nặng lên trong vài giờ.",
    "- Sốt kèm cứng cổ, sợ ánh sáng, đau đầu dữ dội, nôn, lơ mơ là dấu hiệu cần khám ngay.",
    "- Ban đỏ hoặc tím không mất khi ấn vào là dấu hiệu nguy hiểm, phải cấp cứu.",
    "- Không tự dùng kháng sinh hay giảm đau kéo dài trước khi được khám."
  ],
  "uu_tien": 19,
  "khong_khop": [
    "vắc xin",
    "vắc-xin",
    "vaccine",
    "tiêm phòng",
    "tiêm chủng",
    "bụi ... mắt",
    "bụi ... mắt",
    "mắt đau",
    "đau mắt",
    "nhức mắt"
  ]
},
{
  "id": "tre-duoi-3-thang-sot",
  "nhom": "Trẻ dưới 3 tháng tuổi bị sốt",
  "mau": [
    "trẻ dưới 3 tháng sốt",
    "bé dưới 3 tháng sốt",
    "sơ sinh ... sốt",
    "bé 1 tháng ... sốt",
    "bé 2 tháng ... sốt",
    "trẻ 1 tháng ... sốt",
    "trẻ 2 tháng ... sốt",
    "một tháng tuổi ... sốt",
    "hai tháng tuổi ... sốt"
  ],
  "loi_khuyen": [
    "- Đưa trẻ đi khám ngay trong ngày: sốt ở trẻ dưới 3 tháng tuổi luôn cần bác sĩ khám.",
    "- Không tự dùng thuốc hạ sốt hay kháng sinh khi chưa được khám.",
    "- Cho trẻ bú hoặc uống nước từng ngụm nhỏ; theo dõi số lần đi tiểu và nhịp thở.",
    "- Gọi 115 nếu trẻ li bì, bỏ bú, thở nhanh, co giật hoặc tím tái."
  ],
  "uu_tien": 20
},
{
  "id": "mat-nuoc-nang",
  "nhom": "Mất nước nặng ở trẻ",
  "mau": [
    "mất nước nặng",
    "dấu hiệu mất nước",
    "mắt trũng",
    "khóc không có nước mắt",
    "môi khô ... không tiểu",
    "tiêu chảy ... li bì",
    "nôn nhiều ... không tiểu",
    "không đi tiểu ... tiêu chảy",
    "tiêu chảy ... mắt trũng",
    "da mất đàn hồi",
    "mất nước",
    "không có nước mắt",
    "mắt trũng ... da khô"
  ],
  "loi_khuyen": [
    "- Đưa trẻ đến cơ sở y tế ngay, gọi 115 nếu trẻ li bì; mất nước nặng cần truyền dịch, không uống bù đủ được.",
    "- Cho uống từng ngụm nhỏ dung dịch bù nước, không cho uống ừng ực dễ nôn.",
    "- Dấu hiệu nặng: li bì, mắt trũng, môi khô, da mất đàn hồi, không đi tiểu nhiều giờ.",
    "- Tiếp tục cho bú mẹ nếu trẻ còn bú; không tự dùng thuốc cầm tiêu chảy."
  ],
  "uu_tien": 21
},
{
  "id": "mat-thi-luc-dot-ngot",
  "nhom": "Chấn thương mắt, mất thị lực đột ngột",
  "mau": [
    "mất thị lực đột ngột",
    "đột nhiên không nhìn thấy",
    "chấn thương mắt",
    "dị vật vào mắt",
    "vôi bắn vào mắt",
    "hoá chất vào mắt"
  ],
  "loi_khuyen": [
    "- Gọi 115 hoặc đến chuyên khoa mắt ngay: mất thị lực đột ngột là cấp cứu.",
    "- Hoá chất hoặc vôi vào mắt: rửa ngay dưới vòi nước chảy nhẹ liên tục 15 đến 20 phút.",
    "- Không dụi mắt, không tự lấy dị vật, không bôi thuốc nhỏ mắt khi chưa khám.",
    "- Che mắt bằng miếng che sạch, không ấn vào nhãn cầu khi nghi chấn thương."
  ],
  "uu_tien": 32
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

Bối cảnh kỹ thuật, chỉ để hiểu: `uu_tien` nhỏ thì xét trước; `mau` so khớp trên câu hỏi
đã chuẩn hoá; `loi_khuyen` hiện lên đầu câu trả lời; `khong_khop` khớp thì huỷ kết quả;
`kem_theo` phải khớp thêm mới tính.
```
