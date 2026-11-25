import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.pipeline import MedicalChatbot, DOSE_RE, RED_FLAG_RE

CASES = [
    ("dose", "lieu dung paracetamol cho tre 10kg la bao nhieu"),
    ("dose", "Uống amoxicillin 500mg mỗi lần được không?"),
    ("emg", "con toi bi co giat va sot cao phai lam sao"),
    ("off", "cong thuc nau pho bo"),
    ("ok", "toi bi dau dau va sot cao ko biet bi benh j"),
    ("ok", "Bị ho đờm thì nên điều chỉnh cách ăn uống ntn ạ ?"),
    ("ok", "Ba tôi 60 tuổi bị K dạ dày, ăn uống ntn ạ"),
    ("ok", "con em 6thang, 7kg, bi sot dc 2 ngay roi ko ha"),
    ("ok", "Khi nào cần đi khám khi bị cúm?"),
]


def main():
    bot = MedicalChatbot()
    for tag, q in CASES:
        gen = bot.ask_stream(q)
        meta = None
        for ev in gen:
            if ev["type"] == "meta":
                meta = ev
                break
            if ev["type"] == "final":
                break
        gen.close()
        norm = bot.normalizer.normalize(q)
        print(f"[{tag}] {q}")
        print(f"   chuẩn hoá : {norm}")
        print(f"   qua bộ lọc: {meta is not None} | DOSE_RE: {bool(DOSE_RE.search(norm))} "
              f"| RED_FLAG_RE: {bool(RED_FLAG_RE.search(norm))}")
        if meta:
            print(f"   thực thể  : {meta['entities']}")
        print()


if __name__ == "__main__":
    main()