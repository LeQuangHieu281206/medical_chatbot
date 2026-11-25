import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.normalizer import QueryNormalizer, strip_diacritics
from app.services.topic_filter import TopicFilter

OFF = [
    "Công thức nấu phở bò như thế nào?",
    "Cách làm bánh flan mềm mịn",
    "Hôm nay trời Hà Nội có mưa không?",
    "Đội tuyển Việt Nam đá mấy giờ tối nay?",
    "Giá vàng hôm nay bao nhiêu một chỉ?",
    "Làm sao để học giỏi môn toán?",
    "Cách viết vòng lặp for trong Python",
    "Vé máy bay đi Đà Nẵng giá bao nhiêu?",
    "Nên mua điện thoại iPhone hay Samsung?",
    "Thủ tục làm hộ chiếu cần giấy tờ gì?",
    "Bài hát nào đang hot trên TikTok?",
    "Lãi suất gửi tiết kiệm ngân hàng hiện nay là bao nhiêu?",
    "Cách sửa xe máy bị chết máy giữa đường",
    "Giải phương trình bậc hai như thế nào?",
    "Địa điểm du lịch đẹp ở Sa Pa",
    "Cách trồng rau sạch trên sân thượng",
    "Phim nào hay chiếu rạp tuần này?",
    "Làm sao để xin việc ở công ty công nghệ?",
    "Thuê nhà trọ ở Hà Nội giá bao nhiêu?",
    "Cách pha cà phê muối ngon",
    "Viết cho tôi một bài thơ về mùa thu",
    "Cách nấu canh chua cá lóc",
    "Cách cắt tóc nam đẹp hợp mặt tròn",
    "Cách chọn laptop để lập trình",
    # bẫy: có từ giống y tế nhưng ngoài chủ đề
    "Sốt đất ở Hà Nội có giảm không?",
    "Thuốc trừ sâu nào tốt cho cây cam?",
    "Cách chữa cháy khi bị chập điện",
    "Bệnh viện trong game Pokémon nằm ở đâu?",
    # thú y (đã biết là ngoài phạm vi)
    "Con chó nhà tôi bị sốt phải làm sao?",
    "Mèo nhà tôi bị tiêu chảy uống thuốc gì?",
]


def main():
    tf = TopicFilter()
    norm = QueryNormalizer()
    n_orig = n_raw = n_norm = 0
    flagged = []
    for q in OFF:
        noisy = strip_diacritics(q).lower()
        fixed = norm.normalize(noisy)
        a = tf.check(q).allowed
        b = tf.check(noisy).allowed
        c = tf.check(fixed).allowed
        n_orig += a
        n_raw += b
        n_norm += c
        if a or b or c:
            flagged.append((q, a, b, c, fixed))
    n = len(OFF)
    print(f"Số câu ngoài chủ đề: {n}")
    print(f"  lọt qua (câu gốc có dấu)      : {n_orig}")
    print(f"  lọt qua (không dấu, chưa sửa) : {n_raw}")
    print(f"  lọt qua (không dấu, đã chuẩn hoá): {n_norm}")
    if flagged:
        print("\nCác câu lọt qua ở ít nhất một dạng:")
        for q, a, b, c, fixed in flagged:
            print(f"  {q}\n    gốc={a} thô={b} chuẩn hoá={c} | {fixed}")


if __name__ == "__main__":
    main()