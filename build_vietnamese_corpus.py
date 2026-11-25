import os
import re
import random
from collections import defaultdict
from datasets import load_dataset
from tqdm import tqdm

try:
    from underthesea import sent_tokenize
except ImportError:
    sent_tokenize = None

TOTAL_LINES = 300_000
LINES_PER_FILE = 50_000
TOPICS = [
    "gia_dinh",
    "suc_khoe",
    "thoi_su",
    "giao_duc",
    "kinh_doanh",
    "du_lich_am_thuc",
    "cong_nghe",
    "phap_luat",
]
TARGET_PER_TOPIC = TOTAL_LINES // len(TOPICS)  # 37,500 dòng mỗi chủ đề
OUTPUT_DIR = "data/corpus"

VI_DIACRITICS_RE = re.compile(
    r"[àáâãèéêìíòóôõùúăđĩũơưạ-ỹÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠ-Ỹ]"
)
VALID_CHARS_RE = re.compile(
    r"^[A-Za-zÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠ-Ỹàáâãèéêìíòóôõùúăđĩũơưạ-ỹ0-9\s,\.\?\!\:\;\-\–\—\(\)\"\'“”‘’/%]+$"
)
STARTS_UPPER_RE = re.compile(
    r"^[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠ-Ỹ]"
)
ENDS_PUNCT_RE = re.compile(r"[\.\?\!]$")

BANNED_PATTERNS = re.compile(
    r"(http|www\.|\.com|\.vn|\.org|@|#|_|\*|\[|\]|\{|\}|\||<|>|"
    r"xem thêm|đọc thêm|nguồn:|ảnh:|video:|bản quyền|đăng ký ngay|"
    r"theo dõi chúng tôi|bình luận bên dưới|chia sẻ bài viết|"
    r"tôi hy vọng điều này|vui lòng lưu ý rằng|trong bài viết này chúng ta sẽ)",
    re.IGNORECASE,
)

TOPIC_KEYWORDS = {
    "gia_dinh": {
        "gia đình", "bố mẹ", "cha mẹ", "con cái", "vợ chồng", "ông bà", "anh chị em",
        "nhà cửa", "bữa cơm", "nấu ăn", "dọn dẹp", "con nhỏ", "nuôi dạy", "hôn nhân",
        "hàng xóm", "tiết kiệm điện", "cuối tuần", "về quê", "thăm nhà", "sinh hoạt",
        "chăm sóc con", "mẹ chồng", "nàng dâu", "tổ ấm", "việc nhà", "cưới hỏi",
    },
    "suc_khoe": {
        "bác sĩ", "bệnh viện", "sức khỏe", "sức khoẻ", "khám bệnh", "điều trị", "thuốc",
        "triệu chứng", "dinh dưỡng", "tập thể dục", "huyết áp", "tiểu đường", "tim mạch",
        "dạ dày", "cảm cúm", "vắc xin", "tiêm chủng", "xét nghiệm", "phẫu thuật", "giấc ngủ",
        "mất ngủ", "đau đầu", "sốt", "viêm", "bệnh nhân", "y tế", "phòng bệnh", "miễn dịch",
    },
    "thoi_su": {
        "chính phủ", "quốc hội", "thủ tướng", "bộ trưởng", "địa phương", "tỉnh thành",
        "hà nội", "tp.hcm", "thành phố", "giao thông", "môi trường", "biến đổi khí hậu",
        "bão lũ", "thời tiết", "dự án", "hạ tầng", "cao tốc", "quy hoạch", "xã hội",
        "người dân", "cộng đồng", "quốc tế", "ngoại giao", "hội nghị", "sự kiện", "thời sự",
    },
    "giao_duc": {
        "học sinh", "sinh viên", "giáo viên", "giảng viên", "nhà trường", "đại học",
        "học tập", "thi cử", "kỳ thi", "tuyển sinh", "học bổng", "chương trình học",
        "sách giáo khoa", "kiến thức", "kỹ năng", "ngoại ngữ", "tiếng anh", "nghiên cứu",
        "luận văn", "tốt nghiệp", "môn học", "bài tập", "lớp học", "đào tạo", "giáo dục",
    },
    "kinh_doanh": {
        "doanh nghiệp", "kinh doanh", "thị trường", "tài chính", "ngân hàng", "đầu tư",
        "lợi nhuận", "doanh thu", "chi phí", "khách hàng", "sản phẩm", "thương hiệu",
        "khởi nghiệp", "cổ phiếu", "chứng khoán", "lãi suất", "tín dụng", "thu nhập",
        "tiền lương", "chi tiêu", "tiết kiệm", "xuất khẩu", "nhập khẩu", "kinh tế", "giá cả",
    },
    "du_lich_am_thuc": {
        "du lịch", "ẩm thực", "món ăn", "đặc sản", "nhà hàng", "quán ăn", "khách sạn",
        "nghỉ dưỡng", "khám phá", "điểm đến", "danh lam", "bãi biển", "núi rừng",
        "hương vị", "nước mắm", "phở", "bún", "bánh mì", "cà phê", "trà", "nấu nướng",
        "gia vị", "thực đơn", "hành trình", "chuyến đi", "vé máy bay", "phong cảnh",
    },
    "cong_nghe": {
        "công nghệ", "trí tuệ nhân tạo", "phần mềm", "ứng dụng", "dữ liệu", "mạng internet",
        "điện thoại", "máy tính", "bảo mật", "an ninh mạng", "lập trình", "hệ thống",
        "thiết bị", "tự động hóa", "chuyển đổi số", "điện toán", "mạng xã hội", "nền tảng",
        "thuật toán", "cập nhật", "kết nối", "kỹ thuật số", "vi xử lý", "pin", "màn hình",
    },
    "phap_luat": {
        "pháp luật", "luật sư", "tòa án", "nghị định", "thông tư", "quy định", "hành chính",
        "thủ tục", "hồ sơ", "giấy phép", "căn cước", "công chứng", "hợp đồng", "tranh chấp",
        "xử phạt", "vi phạm", "quyền lợi", "nghĩa vụ", "bộ luật", "hiến pháp", "cơ quan",
        "ủy ban", "chứng nhận", "đăng ký", "khiếu nại", "tố tụng", "ban hành", "thuế",
    },
}

SPOKEN_MARKERS = {
    "?", "!", "mình", "tớ", "cậu", "bạn", "anh", "chị", "em", "ơi", "nhé",
    "nhỉ", "ạ", "vậy", "sao", "thế", "quá", "lắm", "cảm ơn", "xin lỗi", "đừng",
}


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if sent_tokenize is not None:
        try:
            return sent_tokenize(text)
        except Exception:
            pass
    return re.split(r"(?<=[\.\?\!])\s+", text)


def clean_sentence(raw: str) -> str | None:
    s = raw.strip()
    s = re.sub(r"^[\-\–\—\•\*\d\.\)\s]+", "", s).strip()
    s = re.sub(r"\s+", " ", s)

    if not STARTS_UPPER_RE.match(s):
        return None
    if not ENDS_PUNCT_RE.search(s):
        return None
    if BANNED_PATTERNS.search(s):
        return None
    if not VALID_CHARS_RE.match(s):
        return None

    # Kiểm tra độ dài: 9-28 tiếng đảm bảo nằm gọn trong 8-30 từ theo cả cách tách tiếng lẫn tách từ ghép
    tokens = s.split()
    if not (9 <= len(tokens) <= 28):
        return None

    # Loại bỏ câu chứa quá nhiều con số (bảng biểu, số liệu rời rạc)
    digit_tokens = sum(1 for t in tokens if any(ch.isdigit() for ch in t))
    if digit_tokens > 2:
        return None

    # Bắt buộc có dấu thanh tiếng Việt tự nhiên (tối thiểu 25% số tiếng mang dấu)
    accented_tokens = sum(1 for t in tokens if VI_DIACRITICS_RE.search(t))
    if accented_tokens < max(3, int(len(tokens) * 0.25)):
        return None

    return s


def classify_topic(sentence: str) -> str | None:
    low = sentence.lower()
    best_topic = None
    best_score = 0

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in low)
        if score > best_score:
            best_score = score
            best_topic = topic

    if best_score >= 2:
        return best_topic
    if best_score == 1 and any(m in low for m in SPOKEN_MARKERS):
        return best_topic
    return None


def iter_text_streams():
    sources = [
        ("HuggingFaceFW/fineweb-2", {"name": "vie_Latn", "split": "train", "streaming": True}, "text"),
        ("wikimedia/wikipedia", {"name": "20231101.vi", "split": "train", "streaming": True}, "text"),
        ("uitnlp/vietnamese_students_feedback", {"split": "train", "streaming": True}, "sentence"),
    ]
    for ds_name, kwargs, field in sources:
        try:
            ds = load_dataset(ds_name, **kwargs)
            for row in ds:
                val = row.get(field)
                if isinstance(val, str) and len(val) > 20:
                    yield val
        except Exception as e:
            print(f"[Canh bao] Bo qua nguon {ds_name}: {e}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    buckets = {t: [] for t in TOPICS}
    seen_hashes = set()

    pbar = tqdm(total=TOTAL_LINES, desc="Thu thap cau tieng Viet")

    for doc in iter_text_streams():
        if all(len(buckets[t]) >= TARGET_PER_TOPIC for t in TOPICS):
            break

        for raw_sent in split_sentences(doc):
            cleaned = clean_sentence(raw_sent)
            if not cleaned:
                continue

            h = hash(cleaned.lower())
            if h in seen_hashes:
                continue

            topic = classify_topic(cleaned)
            if topic is None or len(buckets[topic]) >= TARGET_PER_TOPIC:
                continue

            seen_hashes.add(h)
            buckets[topic].append(cleaned)
            pbar.update(1)

            if all(len(buckets[t]) >= TARGET_PER_TOPIC for t in TOPICS):
                break

    pbar.close()

    all_sentences = []
    for t in TOPICS:
        print(f"Chu de {t}: {len(buckets[t])} dong")
        all_sentences.extend(buckets[t])

    random.seed(42)
    random.shuffle(all_sentences)

    total_written = 0
    num_files = (len(all_sentences) + LINES_PER_FILE - 1) // LINES_PER_FILE
    for idx in range(num_files):
        chunk = all_sentences[idx * LINES_PER_FILE : (idx + 1) * LINES_PER_FILE]
        filename = os.path.join(OUTPUT_DIR, f"corpus_{idx + 1:02d}.txt")
        with open(filename, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(chunk) + "\n")
        total_written += len(chunk)
        print(f"Da ghi {filename}: {len(chunk)} dong")

    print(f"\nHoan tat! Tong cong {total_written} dong.")
    print("\n--- KIEM TRA NGAU NHIEN 20 DONG ---")
    for sample in random.sample(all_sentences, min(20, len(all_sentences))):
        print(sample)


if __name__ == "__main__":
    main()
