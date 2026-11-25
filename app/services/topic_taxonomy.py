"""Bộ nhãn chuyên khoa dùng chung cho audit, validate và báo cáo dữ liệu.

Một nơi duy nhất định nghĩa danh sách chủ đề: `tests/40_data_audit.py` và
`scripts/validate_data.py` đều import từ đây, nên không bị lệch nhãn khi thêm
chủ đề mới.

Thứ tự trong TOPICS là thứ tự ưu tiên khi một câu khớp nhiều chủ đề.
"""
import re

# (nhãn, regex) — xét câu hỏi trước, sau đó tới 400 ký tự đầu của đáp án.
TOPICS = [
    ("ung-thu", r"ung thư|u ác|hóa trị|xạ trị|di căn|khối u"),
    ("tim-mach", r"tim|huyết áp|mạch vành|nhồi máu|loạn nhịp|xơ vữa"),
    ("tieu-duong", r"tiểu đường|đái tháo|đường huyết|insulin"),
    ("than-kinh", r"đột quỵ|tai biến|động kinh|co giật|parkinson|alzheimer|đau nửa đầu"),
    ("tam-than", r"trầm cảm|lo âu|rối loạn tâm thần|mất ngủ|sa sút trí tuệ|tự kỷ"),
    ("ho-hap", r"ho\b|hen|phổi|viêm phổi|cúm|covid|lao\b|khó thở|viêm xoang"),
    ("tieu-hoa", r"dạ dày|tá tràng|ruột|gan\b|mật|táo bón|tiêu chảy|trĩ|viêm đại tràng"),
    ("than-tiet-nieu", r"thận|tiết niệu|bàng quang|sỏi thận|viêm cầu thận"),
    ("nhi-khoa", r"trẻ|bé\b|sơ sinh|nhi\b|mọc răng|bú mẹ|tiêm chủng cho trẻ"),
    ("thai-san", r"mang thai|bầu\b|thai nhi|sau sinh|kinh nguyệt|buồng trứng|hiếm muộn|ivf"),
    ("xuong-khop", r"khớp|xương|gút|gout|cột sống|thoát vị đĩa đệm|lưng|loãng xương"),
    ("da-lieu", r"da\b|mụn|nấm da|ngứa|dị ứng|chàm|vẩy nến|zona"),
    ("mat", r"mắt|thị lực|cận thị|viễn thị|đục thuỷ tinh thể|glôcôm"),
    ("rhm", r"răng|lợi\b|nướu|sâu răng|tuỷ răng"),
    ("tai-mui-hong", r"tai\b|mũi\b|họng|amidan|viêm họng|ù tai|viêm tai"),
    ("thuoc", r"thuốc|paracetamol|kháng sinh|vitamin|tương tác thuốc|tác dụng phụ"),
    ("vaccine", r"vaccine|vắc xin|vắc-xin|tiêm phòng|tiêm chủng"),
    ("dinh-duong", r"dinh dưỡng|ăn uống|thực phẩm|chế độ ăn|béo phì|giảm cân"),
]

TOPIC_RES = [(name, re.compile(pattern, re.I)) for name, pattern in TOPICS]

# Nhãn cho dòng không khớp chủ đề nào ở trên.
FALLBACK_TOPIC = "khac"

TOPIC_NAMES = [name for name, _ in TOPICS] + [FALLBACK_TOPIC]

# Ngưỡng tối thiểu để một chủ đề được coi là có phủ đủ (xem data/DATA_CONTRACT.md).
MIN_ROWS_PER_TOPIC = 400


def tag_topic(question: str, answer: str = "") -> str:
    """Gán nhãn chuyên khoa: xét câu hỏi, rồi 400 ký tự đầu của đáp án."""
    for name, rx in TOPIC_RES:
        if rx.search(question or ""):
            return name
    for name, rx in TOPIC_RES:
        if rx.search((answer or "")[:400]):
            return name
    return FALLBACK_TOPIC
