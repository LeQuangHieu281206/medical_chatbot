import os
from dataclasses import dataclass

import chromadb
import ollama
import re
import unicodedata
from sentence_transformers import SentenceTransformer

DB_PATH = "app/db/chroma_db"
COLLECTION = "medical_kb"
EMBED_MODEL = "intfloat/multilingual-e5-small"
LLM_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

PASS_MAX = 0.12      # nhỏ hơn hoặc bằng: chắc chắn là y tế
REJECT_MIN = 0.14    # lớn hơn: chắc chắn ngoài chủ đề

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

    def _top1_distance(self, query: str) -> float:
        emb = self.embedder.encode([f"query: {query}"], normalize_embeddings=True).tolist()
        res = self.collection.query(query_embeddings=emb, n_results=1)
        return res["distances"][0][0]

    def _ask_llm(self, query: str) -> bool:
        try:
            resp = ollama.chat(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": CLASSIFIER_PROMPT},
                    {"role": "user", "content": query},
                ],
                think=False,
                options={"temperature": 0, "num_predict": 8},
            )
            return resp["message"]["content"].strip().upper().startswith("YES")
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