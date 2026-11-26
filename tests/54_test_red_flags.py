"""Đo bộ nhận diện dấu hiệu cấp cứu (red flag).

Hai chiều:
  - recall: câu có dấu hiệu nguy hiểm phải khớp đúng nhóm
  - precision: câu bệnh thường không được gắn cảnh báo cấp cứu

Câu được đưa qua `QueryNormalizer` trước khi khớp, đúng như `pipeline` làm.
Chỉ đọc, không ghi gì.

Chạy:
    .venv/bin/python tests/54_test_red_flags.py
    .venv/bin/python tests/54_test_red_flags.py -v      # in từng câu sai
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import red_flags  # noqa: E402
from app.services.normalizer import QueryNormalizer  # noqa: E402

# (câu, id nhóm phải khớp)
RED = [
    # đột quỵ
    ("mẹ tôi tự nhiên méo miệng và yếu nửa người bên trái", "dot-quy"),
    ("ông tôi đang nói thì bị nói ngọng, tay phải không nhấc lên được", "dot-quy"),
    ("đau đầu dữ dội đột ngột như búa bổ kèm nôn", "dot-quy"),
    ("nguoi nha toi bi dot quy thi lam gi", "dot-quy"),
    # nhồi máu cơ tim
    ("đau ngực dữ dội lan xuống tay trái và vã mồ hôi", "dau-nguc"),
    ("đau thắt ngực từ sáng, uống thuốc không đỡ", "dau-nguc"),
    ("dau tuc nguc khong tho duoc", "dau-nguc"),
    # khó thở
    ("khó thở không nói được trọn câu, môi tím", "kho-tho"),
    ("bé 8 tháng thở rít và rút lõm lồng ngực", "kho-tho"),
    ("tôi khó thở tăng nhanh từ tối qua", "kho-tho"),
    # sốc phản vệ
    ("uống thuốc xong 10 phút thì sưng môi, nổi mề đay toàn thân", "soc-phan-ve"),
    ("tiêm kháng sinh xong bị khó thở sau khi tiêm", "soc-phan-ve"),
    ("nghi sốc phản vệ sau ăn hải sản", "soc-phan-ve"),
    # ngừng tuần hoàn / mất ý thức
    ("người nhà bất tỉnh, không bắt được mạch", "ngung-tuan-hoan"),
    ("bố tôi ngất rồi không tỉnh lại", "ngung-tuan-hoan"),
    # co giật
    ("con tôi sốt cao co giật 3 phút", "co-giat"),
    ("chồng tôi lên cơn giật tay chân, mắt trợn ngược", "co-giat"),
    # chảy máu
    ("tôi nôn ra máu hai lần từ sáng", "chay-mau"),
    ("đi ngoài phân đen như hắc ín", "chay-mau"),
    ("vết thương chảy máu không cầm được", "chay-mau"),
    # ngộ độc
    ("bé uống nhầm thuốc của ông, giờ lừ đừ", "ngo-doc"),
    ("tôi uống quá nhiều thuốc ngủ", "ngo-doc"),
    ("tôi uống nhầm thuốc diệt chuột", "ngo-doc"),
    # chấn thương
    ("té xe đập đầu, giờ nôn và đau đầu nhiều", "chan-thuong-dau"),
    ("ngã từ trên cao, không cử động được tay chân", "chan-thuong-dau"),
    # đau bụng cấp
    ("đau bụng dữ dội, bụng cứng như gỗ", "dau-bung-cap"),
    ("đau hố chậu phải kèm sốt cao 39 độ", "dau-bung-cap"),
    # sốt xuất huyết
    ("sốt xuất huyết ngày thứ 5, chảy máu chân răng", "sot-xuat-huyet"),
    ("sốt 4 ngày, tay chân lạnh và lừ đừ", "sot-xuat-huyet"),
    # thai sản
    ("đang mang thai 32 tuần bị ra máu âm đạo", "thai-san"),
    ("thai 36 tuần, thai máy giảm rõ rệt", "thai-san"),
    # bỏng / điện / nước
    ("bị điện giật khi sửa ổ cắm", "dien-giat"),
    ("bé bị bỏng nước sôi diện rộng", "bong-nhiet"),
    # hạ đường huyết
    ("mẹ tôi tiểu đường bị hạ đường huyết, run tay vã mồ hôi", "ha-duong-huyet"),
    # toan ceton
    ("con tôi tiểu đường type 1, thở nhanh sâu và có mùi trái cây", "nhiem-toan-ceton"),
    # tự hại
    ("tôi muốn chết, không muốn sống nữa", "tu-hai"),
    ("em nghĩ đến tự tử mỗi đêm", "tu-hai"),
    # 6 nhóm bổ sung sau khi soát
    ("bé bị hóc xương cá, giờ khó thở", "hoc-di-vat"),
    ("đi nắng về ngất, người nóng ran lơ mơ", "soc-nhiet"),
    ("bị rắn lục cắn ở chân, sưng nhanh", "ran-luc"),
    ("mèo cào chảy máu ở tay", "cho-meo-can"),
    ("sốt cao rét run rồi lơ mơ, tay chân lạnh", "nhiem-khuan-huyet"),
    ("trẻ tay chân miệng giật mình chới với", "tay-chan-mieng-nang"),
    # 8 nhóm thêm sau vòng soát y khoa thứ hai
    ("bị ngất khi đang đứng, tỉnh lại sau vài giây", "ngat"),
    ("sốt 39 độ, cứng cổ, sợ ánh sáng", "viem-mang-nao"),
    ("bé 2 tháng tuổi bị sốt 38 độ", "tre-duoi-3-thang-sot"),
    ("trẻ tiêu chảy 3 ngày, mắt trũng, không đi tiểu", "mat-nuoc-nang"),
    ("đau ngực khi hít vào, chân phải sưng và đau", "thuyen-tac-phoi"),
    ("vôi bắn vào mắt, rất rát", "mat-thi-luc-dot-ngot"),
    ("ngã gãy chân, xương lộ ra ngoài", "gay-xuong-vet-thuong"),
    ("tôi đang muốn giết người hàng xóm", "hai-nguoi-khac"),
    ("bị ngạt nước, vớt lên không thở", "duoi-nuoc"),
    # vòng soát thứ năm (chấn thương, chảy máu, nhóm chưa soát)
    ("ngã đập đầu xuống nền, tê yếu tay chân", "chan-thuong-dau"),
    ("tai nạn xe máy, đập đầu xuống đường", "chan-thuong-dau"),
    ("tai nạn xe, đứt chân chảy máu thành tia", "chay-mau"),
    ("đứt lìa ngón tay khi làm máy", "gay-xuong-vet-thuong"),
    ("bé 2 tháng quấy khóc, nóng đầu", "tre-duoi-3-thang-sot"),
    ("sốt 39 độ, cứng cổ, sợ ánh sáng", "viem-mang-nao"),
    ("mạt sắt bắn vào mắt, đau nhiều", "mat-thi-luc-dot-ngot"),
    # vòng soát thứ tư (tai nạn thương tích)
    ("sét đánh khi đang làm ruộng", "dien-giat"),
    ("bị bỏng điện ở tay", "dien-giat"),
    ("uống nhầm thuốc diệt cỏ", "ngo-doc"),
    ("ngộ độc rượu, lơ mơ không gọi được", "ngo-doc"),
    ("sùi bọt mép sau khi uống thuốc", "ngo-doc"),
    ("sưng nề sau rắn cắn, sụp mí mắt", "ran-can"),
    # vòng soát thứ ba
    ("sốt xuất huyết ngày 5, tay chân lạnh và lừ đừ", "sot-xuat-huyet"),
    ("vỡ ối, thấy dây rốn sa ra ngoài âm đạo", "thai-san"),
    # câu gõ không dấu / teencode
    ("be bi co giat, phai lam sao", "co-giat"),
    ("me em bi soc phan ve sau tiem", "soc-phan-ve"),
    ("ba t bi dot quy", "dot-quy"),
    ("uong nham thuoc ha sot cua tre em", "ngo-doc"),
]

# Câu bệnh thường: KHÔNG được gắn cảnh báo cấp cứu
BENIGN = [
    "tôi bị đau đầu nhẹ 2 hôm nay",
    "ho khan về đêm, không sốt",
    "sổ mũi và hắt hơi nhiều khi đổi thời tiết",
    "ngứa da vùng cánh tay sau khi dùng sữa tắm mới",
    "tôi muốn giảm cân, nên ăn gì",
    "đau lưng sau khi ngồi nhiều",
    "kinh nguyệt không đều 3 tháng nay",
    "men gan cao 60, cần kiểm tra gì",
    "trẻ 2 tuổi biếng ăn, có nên bổ sung kẽm",
    "tôi bị trào ngược dạ dày, ăn tối nên kiêng gì",
    "uống cà phê bị run tay nhẹ",
    "huyết áp 130/85 có cao không",
    "đường huyết lúc đói 6,1 có phải tiểu đường",
    "tôi bị mất ngủ, khó vào giấc",
    "rụng tóc nhiều sau sinh",
    "táo bón kéo dài, phân khô",
    "đau khớp gối khi leo cầu thang",
    "tôi bị cúm, sốt 38 độ 2 ngày",
    "viêm họng, ho có đờm xanh",
    "sâu răng hàm dưới bên phải",
    "tôi nên tiêm vaccine cúm vào tháng mấy",
    "bà bầu 3 tháng đầu nên ăn gì",
    "trẻ sơ sinh đi ngoài 5 lần một ngày",
    "mắt tôi bị khô, nhìn màn hình lâu mỏi",
    "tôi bị nấm da ở bàn chân",
    "đau dạ dày khi đói, ăn vào thì đỡ",
    "tôi bị lo âu khi đi làm, tim đập nhanh",
    "sốt 38,5 độ kèm đau họng ở người lớn",
    "tôi bị dị ứng thời tiết, hắt hơi",
    "có nên uống vitamin C mỗi ngày",
    "giá bitcoin hôm nay bao nhiêu",
    "thời tiết Hà Nội mai thế nào",
    "tôi muốn học lập trình",
    "làm sao để ngủ ngon hơn",
    "bé 6 tháng tuổi có nên ăn dặm",
    "tôi bị đau bụng nhẹ khi ăn đồ cay",
    "nước tiểu vàng đậm có sao không",
    "tôi bị chóng mặt khi đứng lên đột ngột",
    # --- từ khoá cấp cứu nhưng ngữ cảnh không nguy hiểm (bẫy báo nhầm) ---
    "tôi bị ngừng thở khi ngủ, ngáy rất to",
    "ngộ độc thực phẩm sau khi ăn hải sản",
    "ăn gì để hạ đường huyết",
    "cách hạ đường huyết tại nhà",
    "uống thuốc hạ đường huyết bị tiêu chảy",
    "bé chảy máu cam thường xuyên, không sốt",
    "kinh nguyệt ra máu âm đạo nhiều ngày",
    "đường huyết 200 có sao không",
    "đau ngực nhẹ khi hít vào sâu, không khó thở",
    "tôi ho ra máu ít một lần năm ngoái",
    "sốt xuất huyết có lây từ người sang người không",
]

# Câu hỏi THÔNG TIN về bệnh mạn tính: hiện vẫn nhận cảnh báo có điều kiện
# ("Nếu đây là tình huống khẩn cấp..."). Đây là đánh đổi đã biết: thà cảnh báo
# thừa còn hơn bỏ sót cơn cấp. Không tính vào tỉ lệ báo nhầm.
KNOWN_NOISY = [
    "tôi bị động kinh đã 20 năm, uống thuốc đều",
    "điều trị động kinh bằng cách nào",
]


def main():
    ap = argparse.ArgumentParser(description="Đo bộ red flag")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    norm = QueryNormalizer()
    flags = red_flags.load_flags()
    print(f"{len(flags)} nhóm, "
          f"{sum(len(f.pattern.pattern.split('|')) for f in flags)} mẫu, "
          f"{sum(1 for f in flags if f.veto or f.must)} nhóm có luật loại trừ/bắt buộc\n")

    ok = 0
    wrong = []
    for q, want in RED:
        got = red_flags.match(norm.normalize(q))
        got_id = got.id if got else None
        if got_id == want:
            ok += 1
        else:
            wrong.append((q, want, got_id))
    print(f"Recall  : {ok}/{len(RED)} = {100 * ok / len(RED):.1f}%")
    if args.verbose:
        for q, want, got in wrong:
            print(f"   [sai] {q[:60]!r} -> {got} (mong đợi {want})")

    fp = [(q, red_flags.match(norm.normalize(q))) for q in BENIGN]
    fp = [(q, f) for q, f in fp if f]
    print(f"Báo nhầm: {len(fp)}/{len(BENIGN)} = {100 * len(fp) / len(BENIGN):.1f}%")
    for q, f in fp:
        print(f"   [nhầm] {q!r} -> {f.nhom}")

    # Lời khuyên không được chứa liều thuốc
    dose = re.compile(r"\d+\s*(mg|mcg|ml|gói|ống|viên)\b", re.IGNORECASE)
    bad_dose = [(f.id, line) for f in flags for line in f.loi_khuyen if dose.search(line)]
    print(f"Liều trong lời khuyên: {len(bad_dose)} dòng")
    for f_id, line in bad_dose:
        print(f"   [{f_id}] {line[:70]}")

    # Khối cảnh báo phải nhắc 115 hoặc đi viện
    miss = [f.id for f in flags
            if not any(("115" in l) or ("viện" in l) or ("cấp cứu" in l) for l in f.loi_khuyen)]
    print(f"Nhóm không nhắc 115/đi viện: {len(miss)} {miss}")

    noisy = [(q, red_flags.match(norm.normalize(q))) for q in KNOWN_NOISY]
    noisy = [(q, f) for q, f in noisy if f]
    print(f"Đánh đổi đã biết (vẫn cảnh báo): {len(noisy)}/{len(KNOWN_NOISY)}")

    bad = len(wrong) + len(fp) + len(bad_dose) + len(miss)
    print("\n" + ("ĐẠT" if bad == 0 else f"CÒN {bad} vấn đề"))


if __name__ == "__main__":
    main()
