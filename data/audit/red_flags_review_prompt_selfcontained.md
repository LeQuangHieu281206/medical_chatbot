# Prompt tự chứa (không cần đính kèm file)

Dán toàn bộ nội dung trong khối dưới đây vào Claude / ChatGPT. Bản này đã kèm dữ liệu.

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

Nội dung file `red_flags.jsonl` hiện tại:

{"id": "tu-hai", "nhom": "Nguy cơ tự hại", "uu_tien": 1, "mau": ["tự tử", "tự sát", "muốn chết", "nghĩ đến cái chết", "không muốn sống", "tự làm đau bản thân", "cắt tay", "uống thuốc tự tử", "nhảy lầu"], "loi_khuyen": ["- Đừng ở một mình: hãy nhờ một người thân ở bên bạn ngay bây giờ.", "- Gọi 115 nếu bạn đã làm mình bị thương, hoặc đến khoa cấp cứu gần nhất.", "- Có thể gọi đường dây nóng tâm lý miễn phí của Bệnh viện Tâm thần Trung ương hoặc tổng đài 1800 599 920 để nói chuyện ngay.", "- Tránh xa thuốc, dao, vật sắc nhọn và nơi nguy hiểm trong lúc này."]}
{"id": "dot-quy", "nhom": "Nghi đột quỵ", "uu_tien": 2, "mau": ["đột quỵ", "tai biến", "méo miệng", "liệt nửa người", "yếu nửa người", "nói ngọng", "nói khó đột ngột", "nhìn mờ đột ngột", "tê nửa người", "đau đầu dữ dội đột ngột", "không nhấc được tay"], "loi_khuyen": ["- Gọi 115 ngay và ghi lại chính xác giờ khởi phát triệu chứng (mốc quan trọng để bác sĩ quyết định can thiệp).", "- Không cho ăn uống, không tự cho uống thuốc hạ huyết áp hay an cần.", "- Đặt người bệnh nằm nghiêng an toàn nếu nôn hoặc mất ý thức, nới lỏng quần áo.", "- Không chờ xem có tự khỏi; mỗi phút chậm trễ đều làm giảm khả năng hồi phục."]}
{"id": "soc-phan-ve", "nhom": "Nghi sốc phản vệ", "uu_tien": 3, "mau": ["sốc phản vệ", "sưng môi", "sưng lưỡi", "nổi mề đay toàn thân", "khó thở sau khi tiêm", "khó thở sau khi uống thuốc", "ngất sau tiêm", "phát ban toàn thân"], "loi_khuyen": ["- Gọi 115 ngay, nói rõ nghi sốc phản vệ và thuốc/thức ăn vừa dùng.", "- Cho người bệnh nằm, đầu thấp, chân cao; không đứng dậy đi lại.", "- Nếu có bút tiêm adrenalin do bác sĩ kê, dùng theo đúng hướng dẫn đã được tập.", "- Không chờ đỡ rồi mới đi viện: sốc phản vệ có thể nặng lên rất nhanh."]}
{"id": "ngung-tuan-hoan", "nhom": "Ngừng thở, ngừng tim, mất ý thức", "uu_tien": 4, "mau": ["ngừng thở", "ngừng tim", "không bắt được mạch", "bất tỉnh", "hôn mê", "không tỉnh", "mất ý thức", "ngất", "tím tái"], "loi_khuyen": ["- Gọi 115 và nhờ người khác mang máy sốc điện tự động nếu có.", "- Nếu người bệnh không thở hoặc chỉ thở ngáp: ép tim ngoài lồng ngực ngay, khoảng 100 đến 120 lần mỗi phút, sâu 5 đến 6 cm, không dừng cho tới khi có người hỗ trợ.", "- Nếu còn thở: đặt nằm nghiêng an toàn và theo dõi sát nhịp thở."]}
{"id": "dau-nguc", "nhom": "Nghi nhồi máu cơ tim, đau ngực cấp", "uu_tien": 5, "mau": ["đau ngực", "đau thắt ngực", "đau tức ngực", "đau ngực lan", "bóp nghẹt ngực", "nặng ngực", "đau tay trái kèm mệt"], "loi_khuyen": ["- Gọi 115, không tự lái xe đến viện.", "- Ngồi hoặc nằm đầu cao, ngừng mọi gắng sức, cởi bỏ đồ chật.", "- Không tự dùng thuốc khi chưa có chỉ định của bác sĩ, trừ thuốc đã được kê cho chính bạn.", "- Đau ngực kéo dài trên 15 phút hoặc kèm vã mồ hôi, khó thở là cấp cứu, không chờ."]}
{"id": "nhiem-toan-ceton", "nhom": "Nghi nhiễm toan ceton do đái tháo đường", "uu_tien": 6, "mau": ["nhiễm toan ceton", "thở nhanh sâu", "mùi ceton", "mùi trái cây", "đường huyết rất cao", "đường huyết 20"], "loi_khuyen": ["- Đến cấp cứu ngay, đây là biến chứng nguy hiểm của đái tháo đường.", "- Không tự tiêm thêm insulin khi chưa được bác sĩ hướng dẫn trong tình huống này.", "- Mang theo máy đo, sổ ghi đường huyết và thuốc đang dùng khi đi viện."]}
{"id": "co-giat", "nhom": "Co giật", "uu_tien": 7, "mau": ["co giật", "động kinh", "lên cơn giật", "giật tay chân", "sốt cao co giật", "co cứng toàn thân"], "loi_khuyen": ["- Gọi 115 nếu cơn kéo dài trên 5 phút, lặp lại, hoặc người bệnh không tỉnh lại sau cơn.", "- Không đưa bất kỳ vật gì vào miệng và không giữ chặt tay chân người đang co giật.", "- Đặt người bệnh nằm nghiêng, kê đầu mềm, nới lỏng quần áo, bấm giờ cơn giật.", "- Với trẻ sốt cao co giật: hạ sốt bằng paracetamol đúng liều trên nhãn theo cân nặng và đưa đi khám."]}
{"id": "ha-duong-huyet", "nhom": "Hạ đường huyết nặng", "uu_tien": 7, "mau": ["hạ đường huyết", "tụt đường huyết", "run tay vã mồ hôi", "lú lẫn vì đói"], "loi_khuyen": ["- Nếu còn tỉnh và nuốt được: cho uống nước đường, nước ngọt hoặc viên glucose ngay.", "- Nếu đã lú lẫn, co giật hoặc không nuốt được: gọi 115, không đổ nước vào miệng.", "- Kiểm tra lại đường huyết sau khoảng 15 phút và cho ăn thêm tinh bột khi đã tỉnh."]}
{"id": "kho-tho", "nhom": "Khó thở nặng", "uu_tien": 8, "mau": ["khó thở", "thở rít", "rút lõm lồng ngực", "thở rên", "không nói được câu", "thở nhanh", "ho ra máu", "suy hô hấp"], "loi_khuyen": ["- Gọi 115 nếu người bệnh không nói được trọn câu, môi tím hoặc phải ngồi chống tay để thở.", "- Cho ngồi thẳng hoặc nửa nằm, không nằm ngửa, nới lỏng quần áo.", "- Với trẻ nhỏ: bế đúng tư thế, không ép nằm, đếm nhịp thở mỗi phút để báo cho nhân viên y tế."]}
{"id": "chay-mau", "nhom": "Chảy máu, xuất huyết tiêu hoá", "uu_tien": 8, "mau": ["chảy máu nhiều", "chảy máu không cầm", "nôn ra máu", "đi ngoài phân đen", "phân đen", "máu chảy thành tia", "đi cầu ra máu tươi"], "loi_khuyen": ["- Gọi 115 hoặc đến cấp cứu ngay; không ăn uống gì để phòng khi cần nội soi.", "- Vết thương chảy máu ngoài da: ấn trực tiếp bằng gạc sạch, giữ liên tục và kê cao vùng bị thương.", "- Không tự dùng thuốc giảm đau chống viêm nhóm ibuprofen, aspirin khi đang chảy máu."]}
{"id": "ngo-doc", "nhom": "Ngộ độc, quá liều thuốc", "uu_tien": 9, "mau": ["quá liều", "ngộ độc", "uống nhầm", "uống quá nhiều thuốc", "quá nhiều thuốc", "uống thuốc diệt chuột", "uống xăng", "uống dầu hoả", "uống acid", "uống thuốc ngủ"], "loi_khuyen": ["- Gọi 115 ngay và giữ lại vỏ thuốc, hộp thuốc, đơn thuốc để bác sĩ biết đã dùng gì.", "- Không tự gây nôn, đặc biệt khi nghi đã uống xăng dầu hoặc chất tẩy ăn mòn.", "- Không tự cho uống than hoạt hoặc sữa khi chưa có hướng dẫn của nhân viên y tế.", "- Nếu người bệnh hôn mê: đặt nằm nghiêng an toàn và theo dõi nhịp thở trên đường đi viện."]}
{"id": "chan-thuong-dau", "nhom": "Chấn thương đầu, cột sống", "uu_tien": 10, "mau": ["đập đầu", "chấn thương đầu", "ngã từ trên cao", "tai nạn xe", "chấn thương cột sống", "không cử động được tay chân", "nôn sau khi đập đầu", "chảy máu tai sau ngã"], "loi_khuyen": ["- Gọi 115; không tự di chuyển nạn nhân nếu nghi chấn thương cổ, cột sống.", "- Giữ đầu và cổ thẳng theo trục cơ thể, cố định bằng hai tay hoặc vật mềm hai bên đầu.", "- Không cho ăn uống; theo dõi ý thức, nôn, đau đầu tăng dần và báo cho nhân viên y tế."]}
{"id": "dau-bung-cap", "nhom": "Đau bụng cấp, bụng ngoại khoa", "uu_tien": 11, "mau": ["đau bụng dữ dội", "bụng cứng", "bụng cứng như gỗ", "đau bụng kèm sốt cao", "không trung tiện", "bụng chướng căng", "đau hố chậu phải"], "loi_khuyen": ["- Đến cấp cứu ngay; không ăn uống để phòng khi phải can thiệp ngoại khoa.", "- Không tự dùng thuốc giảm đau vì sẽ che mất dấu hiệu bác sĩ cần khám.", "- Không đắp nóng, không nắn bóp bụng; nằm nghiêng co gối cho dễ chịu."]}
{"id": "sot-xuat-huyet", "nhom": "Sốt xuất huyết có dấu hiệu cảnh báo", "uu_tien": 12, "mau": ["sốt xuất huyết", "chảy máu chân răng", "chảy máu cam", "tay chân lạnh", "lừ đừ", "nôn nhiều", "đau bụng dữ dội khi sốt"], "loi_khuyen": ["- Đến bệnh viện hoặc cơ sở y tế ngay trong ngày, đặc biệt từ ngày thứ 3 đến ngày thứ 7 của bệnh.", "- Chỉ dùng paracetamol để hạ sốt; không dùng aspirin, ibuprofen vì làm tăng nguy cơ chảy máu.", "- Uống nước điện giải từng ngụm nhỏ, theo dõi sốt và lượng nước tiểu."]}
{"id": "thai-san", "nhom": "Cấp cứu thai sản", "uu_tien": 13, "mau": ["ra máu âm đạo", "đau bụng khi mang thai", "vỡ ối", "thai máy giảm", "thai không cử động", "co giật khi mang thai", "nhìn mờ khi mang thai", "phù nề khi mang thai"], "loi_khuyen": ["- Đến ngay khoa sản của bệnh viện gần nhất, không chờ tái khám theo lịch.", "- Nằm nghiêng trái, theo dõi cử động thai và lượng máu ra, ghi lại thời điểm bắt đầu.", "- Gọi 115 nếu có co giật, đau đầu dữ dội, nhìn mờ hoặc chảy máu nhiều."]}
{"id": "bong-dien", "nhom": "Bỏng, điện giật, đuối nước", "uu_tien": 14, "mau": ["bỏng nặng", "bỏng rộng", "bỏng điện", "điện giật", "đuối nước", "ngạt nước", "bỏng nước sôi", "bỏng diện rộng", "bị bỏng", "phỏng nước sôi"], "loi_khuyen": ["- Điện giật: ngắt nguồn điện trước khi chạm vào người bệnh.", "- Bỏng: làm mát vùng bỏng bằng nước sạch mát chảy nhẹ khoảng 20 phút, không dùng đá lạnh, không bôi kem đánh răng hay mắm.", "- Đuối nước: gọi 115, mở thông đường thở, ép tim nếu không thở."]}
```
