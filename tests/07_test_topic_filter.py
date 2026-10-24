import sys
import time

sys.path.insert(0, ".")

from app.services.topic_filter import TopicFilter

# True: phải cho qua, False: phải chặn, None: ranh giới, bạn tự quyết định
CASES = [
    ("Trẻ bị sốt cao co giật thì xử lý thế nào?", True),
    ("đau đầu", True),
    ("tiểu đường là gì", True),
    ("nổi mề đay do đâu", True),
    ("Giá vaccine Covid-19 bao nhiêu?", True),
    ("Bị chó cắn có cần tiêm phòng dại không?", True),
    ("Ăn thịt gà có tốt cho người bị gout không?", True),
    ("Nên ăn gì để giảm cân?", None),
    ("Chế độ ăn keto là gì?", None),
    ("Công thức nấu phở bò", False),
    ("Giá bitcoin hôm nay bao nhiêu?", False),
    ("Kể một câu chuyện cười", False),
    ("Mua laptop nào tốt dưới 20 triệu", False),
    ("Thủ đô của Pháp là gì?", False),
    ("Viết code Python đảo ngược chuỗi", False),
    ("Con chó nhà tôi bị sốt phải làm sao?", False),
    ("Con mèo bị nôn mửa nên làm gì?", False),
    ("Cho thú cưng ăn gì khi bị tiêu chảy?", False),
    ("Nhân vật trong phim bị ung thư là phim nào?", False),
]

flt = TopicFilter()
wrong = 0
for q, expected in CASES:
    t0 = time.time()
    r = flt.check(q)
    ms = int((time.time() - t0) * 1000)
    mark = "  "
    if expected is not None and r.allowed != expected:
        mark = "!!"
        wrong += 1
    print(f"{mark} {'CHO QUA' if r.allowed else 'CHẶN  '} | {r.distance:.3f} | {r.zone:6} | {ms:5d} ms | {q}")

print(f"\nSai so với kỳ vọng: {wrong}")