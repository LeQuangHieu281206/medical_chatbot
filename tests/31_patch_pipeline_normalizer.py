import py_compile
import shutil
import sys
from pathlib import Path

PATH = Path("app/services/pipeline.py")

EDITS = [
    ("class MedicalChatbot:\n",
     "from app.services.normalizer import QueryNormalizer\n\n\nclass MedicalChatbot:\n"),
    ("        self.topic = TopicFilter()\n",
     "        self.topic = TopicFilter()\n        self.normalizer = QueryNormalizer()\n"),
    ('            return Answer("Bạn hãy nhập câu hỏi về sức khoẻ nhé.", allowed=False)\n\n        timings = {}\n',
     '            return Answer("Bạn hãy nhập câu hỏi về sức khoẻ nhé.", allowed=False)\n\n'
     '        original = question\n'
     '        question = self.normalizer.normalize(question)\n\n'
     '        timings = {}\n'
     '        if question != original:\n'
     '            timings["chuan_hoa"] = question\n'),
    ('        try:\n            topic = self.topic.check(question)\n',
     '        original = question\n'
     '        question = self.normalizer.normalize(question)\n\n'
     '        try:\n            topic = self.topic.check(question)\n'),
    ('yield {"type": "meta", "topic": topic, "entities": entities}',
     'yield {"type": "meta", "topic": topic, "entities": entities,\n'
     '               "normalized": question if question != original else None}'),
]


def main():
    text = PATH.read_text(encoding="utf-8")
    if "self.normalizer" in text:
        print("pipeline.py đã được vá, không làm gì thêm.")
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
    print("Đã vá và biên dịch OK. Bản sao lưu: pipeline.py.bak")


if __name__ == "__main__":
    main()