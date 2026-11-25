import py_compile
import shutil
import sys
from pathlib import Path

PATH = Path("app/services/normalizer.py")

EDITS = [
    ("    def expand_teencode(self, text: str) -> str:\n",
     "    def expand_teencode(self, text: str, accented: bool = True) -> str:\n"),
    ("            rep = TEEN.get(w.lower())\n",
     "            rep = TEEN.get(w.lower())\n"
     "            if rep and not accented and self._ambiguous(w.lower()):\n"
     "                rep = None   # câu không dấu: để bộ khôi phục dấu quyết định\n"),
    ("    # ---- phát hiện câu thiếu dấu ----\n",
     "    def _ambiguous(self, key: str) -> bool:\n"
     '        """Từ teencode trùng với âm tiết không dấu có thật (vd. tui ~ túi)."""\n'
     "        return key.isascii() and any(\n"
     "            f != key and has_marks(f) for f in self.forms.get(key, []))\n\n"
     "    # ---- phát hiện câu thiếu dấu ----\n"),
    ("        text = self.expand_teencode(text)\n"
     "        if self.accent_ratio(text) < ACCENT_RATIO_MIN:\n"
     "            text = self.restore_diacritics(text)\n",
     "        accented = self.accent_ratio(text) >= ACCENT_RATIO_MIN\n"
     "        text = self.expand_teencode(text, accented)\n"
     "        if not accented:\n"
     "            text = self.restore_diacritics(text)\n"),
]


def main():
    text = PATH.read_text(encoding="utf-8")
    if "_ambiguous" in text:
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