import py_compile
import shutil
import sys
from pathlib import Path

PATH = Path("app/services/normalizer.py")

EDITS = [
    ("        return key.isascii() and any(\n"
     "            f != key and has_marks(f) for f in self.forms.get(key, []))\n",
     "        k = self.uni.get(key, 0)\n"
     "        return key.isascii() and any(\n"
     "            f != key and has_marks(f) and f not in TEEN\n"
     "            and self.uni.get(f, 0) >= max(10, 3 * k)\n"
     "            for f in self.forms.get(key, []))\n"),
    ('    "nhg": "những", "nhưg": "nhưng", "nhug": "nhưng",\n',
     '    "nhg": "những", "nhưg": "nhưng", "nhug": "nhưng", "nhìu": "nhiều",\n'),
]


def main():
    text = PATH.read_text(encoding="utf-8")
    if "3 * k" in text:
        print("normalizer.py đã được vá, không làm gì thêm.")
        return
    for i, (old, _) in enumerate(EDITS, 1):
        n = text.count(old)
        if n != 1:
            print(f"Điểm neo {i} khớp {n} lần (cần đúng 1), dừng, chưa sửa gì.")
            sys.exit(1)
    for old, new in EDITS:
        text = text.replace(old, new, 1)
    shutil.copy(PATH, PATH.with_suffix(".py.bak"))
    PATH.write_text(text, encoding="utf-8")
    py_compile.compile(str(PATH), doraise=True)
    print("Đã vá và biên dịch OK. Bản sao lưu: normalizer.py.bak")


if __name__ == "__main__":
    main()