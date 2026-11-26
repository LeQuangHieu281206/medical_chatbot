import os
from pathlib import Path
from dataclasses import dataclass

import chromadb
import re
import unicodedata
from sentence_transformers import SentenceTransformer

from app.services import llm

DB_PATH = "app/db/chroma_db"
# Dấu model đã dùng để nhúng KB. Ghi lúc nạp KB; đọc lúc truy vấn để phát hiện
# trường hợp KB cũ bị dùng với model mới (vector lệch, truy xuất rác, không lỗi).
EMBED_STAMP = Path(DB_PATH).parent / "embed_model.txt"
# Mặc định dùng bản đã bổ sung vaccine/dinh dưỡng (medical_kb_v3). Muốn quay lại
# bản cũ thì chạy: KB_COLLECTION=medical_kb .venv/bin/python app/api/server.py
COLLECTION = os.getenv("KB_COLLECTION", "medical_kb_v3")
# Kho bách khoa (bài viết y khoa) là collection RIÊNG, không phụ thuộc phiên bản KB.
# Trước đây pipeline tự ghép f"{COLLECTION}_vimedaqa" nên khi đổi KB sang v3 thì
# thành "medical_kb_v3_vimedaqa" — không tồn tại, mất toàn bộ bài bách khoa.
ENCY_COLLECTION = os.getenv("KB_ENCY_COLLECTION", "medical_kb_vimedaqa")
# Model nhúng: ĐỔI ĐƯỢC bằng env, nhưng đổi model thì PHẢI nạp lại toàn bộ KB và
# hiệu chuẩn lại PASS_MAX/REJECT_MIN (mỗi model có thang khoảng cách khác nhau).
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
LLM_MODEL = llm.OLLAMA_MODEL      # giữ tên cũ cho code/test đang import

PASS_MAX = float(os.getenv("TOPIC_PASS_MAX", "0.12"))   # <= : chắc chắn là y tế
REJECT_MIN = float(os.getenv("TOPIC_REJECT_MIN", "0.14"))  # > : chắc chắn ngoài chủ đề

ANIMAL_PATTERN = re.compile(
    r"\b(chó|mèo|thú cưng|thú y|vật nuôi|gà|vịt|heo|lợn|trâu|bò|ngựa|cá cảnh|chim cảnh|cây trồng)\b",
    re.IGNORECASE,
)

REFUSAL = (
    "Mình chỉ hỗ trợ các câu hỏi về sức khoẻ và y tế. "
    "Bạn có thể hỏi về triệu chứng, bệnh, thuốc, phòng bệnh hoặc chăm sóc sức khoẻ nhé."
)

CLASSIFIER_PROMPT = (
    "Bạn là bộ phân loại chủ đề. Chỉ trả lời đúng một từ: YES hoặc NO.\n"
    "YES nếu câu hỏi thuộc lĩnh vực sức khoẻ, y tế, bệnh tật, thuốc, vaccine, "
    "hoặc dinh dưỡng và vận động liên quan đến sức khoẻ của con người.\n"
    "NO với mọi chủ đề khác (giải trí, công nghệ, tài chính, nấu ăn, thú y, truyện phim...)."
)


@dataclass
class TopicResult:
    allowed: bool
    distance: float
    zone: str    # "pass", "grey" hoặc "reject"
    reason: str


class TopicFilter:
    def __init__(self, embedder=None, collection=None):
        self.embedder = embedder or SentenceTransformer(EMBED_MODEL)
        self.collection = collection or chromadb.PersistentClient(
            path=DB_PATH
        ).get_collection(COLLECTION)
        self.model_mismatch = self._check_embed_model()

    def _check_embed_model(self) -> str | None:
        """Cảnh báo nếu KB được nhúng bằng model KHÁC model đang cấu hình.

        Lỗi này không gây exception — vector vẫn "chạy" nhưng truy xuất ra rác,
        nên phải kiểm tra tường minh. Dấu được ghi lúc nạp KB (ingest_kb.py).
        """
        try:
            built = (self.collection.metadata or {}).get("embed_model")
        except Exception:
            built = None
        if not built:
            try:
                built = EMBED_STAMP.read_text(encoding="utf-8").strip() or None
            except Exception:
                built = None
        if not built or built == EMBED_MODEL:
            return None
        msg = (f"KB [{COLLECTION}] được nhúng bằng '{built}' nhưng đang cấu hình "
               f"'{EMBED_MODEL}'. Truy xuất sẽ sai. Nạp lại KB hoặc đặt "
               f"EMBED_MODEL={built}.")
        print(f"[topic_filter] CẢNH BÁO: {msg}")
        return msg

    def _top1_distance(self, query: str) -> float:
        emb = self.embedder.encode([f"query: {query}"], normalize_embeddings=True).tolist()
        res = self.collection.query(query_embeddings=emb, n_results=1)
        return res["distances"][0][0]

    def _ask_llm(self, query: str) -> bool:
        try:
            text = llm.chat(
                [
                    {"role": "system", "content": CLASSIFIER_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=0,
                max_tokens=8,
                fast=True,          # phân loại chỉ cần model rẻ, đừng dùng model lớn
            )
            return text.strip().upper().startswith("YES")
        except Exception as e:
            print("Lỗi gọi LLM phân loại:", e)
            return False  # lỗi thì từ chối cho an toàn

    def check(self, query: str) -> TopicResult:
        query = unicodedata.normalize("NFC", query)
        d = self._top1_distance(query)
        if d > REJECT_MIN:
            return TopicResult(False, d, "reject", "xa dữ liệu y tế")
        if d <= PASS_MAX and not ANIMAL_PATTERN.search(query):
            return TopicResult(True, d, "pass", "gần dữ liệu y tế")
        ok = self._ask_llm(query)
        zone = "grey" if d > PASS_MAX else "animal"
        return TopicResult(ok, d, zone, "LLM phân loại: " + ("YES" if ok else "NO"))