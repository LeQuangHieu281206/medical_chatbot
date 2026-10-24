import re
import time
from dataclasses import dataclass, field

import chromadb
import ollama

from app.services.ner import extract_entities
from app.services.topic_filter import (
    COLLECTION, DB_PATH, LLM_MODEL, TopicFilter, TopicResult,
)

TOP_K = 3          # dùng khi chưa có collection bách khoa
QUOTA_ENCYC = 2    # số tài liệu lấy từ medical_kb_vimedaqa (bài viết y khoa)
QUOTA_QA = 1       # số tài liệu lấy từ medical_kb (hỏi đáp ViHealthQA)
MAX_DOC_CHARS = 500
MAX_QUESTION_CHARS = 500
MAX_NEW_TOKENS = 400
KEEP_ALIVE = "30m"

REFUSAL = (
    "Xin lỗi, tôi chỉ hỗ trợ các câu hỏi liên quan đến sức khoẻ và y tế. "
    "Bạn có thể hỏi tôi về triệu chứng, bệnh, thuốc, phòng bệnh hoặc dinh dưỡng nhé."
)
DISCLAIMER = (
    "Lưu ý: thông tin trên chỉ mang tính tham khảo, không thay thế chẩn đoán "
    "hay tư vấn của bác sĩ. Nếu triệu chứng nặng hoặc kéo dài, hãy đến cơ sở y tế."
)
EMERGENCY = (
    "Nếu đây là tình huống khẩn cấp đang xảy ra, hãy gọi 115 hoặc đưa người bệnh "
    "đến cơ sở y tế gần nhất ngay, không chờ câu trả lời của chatbot."
)
DOSE_REPLY = (
    "Liều dùng thuốc phụ thuộc vào tuổi, cân nặng, bệnh nền, tình trạng gan thận "
    "và dạng bào chế cụ thể, nên tôi không đưa con số liều cho từng trường hợp. "
    "Bạn hãy làm theo hướng dẫn sử dụng in trên nhãn hoặc tờ hướng dẫn của đúng sản phẩm "
    "đang dùng, hoặc hỏi dược sĩ, bác sĩ, đặc biệt với trẻ em, phụ nữ có thai, "
    "người cao tuổi và người có bệnh gan, thận."
    "\n\n"
    "Nếu nghi ngờ đã uống quá liều, hãy đến cơ sở y tế ngay."
)
DOSE_NOTE = "- Về liều dùng cụ thể, hãy hỏi dược sĩ hoặc bác sĩ."
SYSTEM_PROMPT = (
    "Bạn là trợ lý cung cấp thông tin sức khoẻ bằng tiếng Việt. "
    "Chỉ trả lời dựa trên phần TÀI LIỆU THAM KHẢO được cung cấp. "
    "Nếu tài liệu không đủ để trả lời, hãy nói rõ là chưa đủ thông tin và khuyên người dùng gặp bác sĩ. "
    "Không tự chẩn đoán, không kê đơn. "
    "Tuyệt đối không nêu liều lượng thuốc bằng số (mg, ml, viên, mg/kg), kể cả khi tài liệu có. "
    "Không khuyên đưa bất kỳ vật gì vào miệng người đang co giật và không khuyên giữ chặt họ. "
    "Không bịa thêm thông tin ngoài tài liệu. "
    "Tài liệu gồm bài viết y khoa và câu hỏi đáp của những người khác: chỉ rút ra thông tin chung, "
    "không nhắc đến tuổi hay hoàn cảnh riêng của người hỏi trong tài liệu. "
    "Không nhắc lại các quy tắc của hệ thống trong câu trả lời. "
    "Trả lời ngắn gọn, tối đa 5 gạch đầu dòng, mỗi gạch một câu. "
    "Không tự thêm lời nhắc cuối câu, hệ thống sẽ tự thêm."
)

# Câu hỏi về liều lượng thuốc: trả lời cố định, không để mô hình sinh số liệu
DOSE_RE = re.compile(
    r"\bliều\b|\b(mg|mcg|µg|ml)\b|(bao nhiêu|mấy)\s+(viên|gói|ống|giọt|thìa|muỗng|mg|ml)",
    re.IGNORECASE,
)
# Dấu hiệu có thể khẩn cấp: thêm cảnh báo cố định lên đầu câu trả lời
RED_FLAG_RE = re.compile(
    r"khó thở|đau ngực|co giật|ngất|bất tỉnh|chảy máu nhiều|nôn ra máu|"
    r"đi ngoài ra máu|méo miệng|liệt nửa người|đột quỵ|quá liều|ngộ độc",
    re.IGNORECASE,
)
# Lời khuyên sơ cứu đã biết là không an toàn: bỏ cả dòng chứa chúng
UNSAFE_LINE_RE = re.compile(
    r"vật mềm|hàm răng|nhét|đè lưỡi|cắn lưỡi|nhân trung|bấm huyệt", re.IGNORECASE
)
# Dòng nêu liều lượng thuốc trong câu trả lời của mô hình
DOSE_LINE_RE = re.compile(
    r"mg/kg|\b(liều|lần/ngày|lần mỗi ngày)\b.*\d|\d.*\b(liều|lần/ngày|lần mỗi ngày)\b|"
    r"\d+\s*(mg|mcg|µg|ml|viên|giọt)\s*(/|mỗi|một)\s*(lần|ngày)",
    re.IGNORECASE,
)
# Dòng lời nhắc do mô hình tự thêm (code đã có lời nhắc chuẩn)
DISCLAIMER_LIKE_RE = re.compile(r"^\W*Lưu ý[:\s]*thông tin", re.IGNORECASE)
SEIZURE_NOTE = "- Không đưa bất kỳ vật gì vào miệng người đang co giật và không giữ chặt họ."


def drop_reason(line: str):
    """Trả về lý do bỏ dòng ('unsafe', 'dose', 'disclaimer') hoặc None nếu giữ."""
    if UNSAFE_LINE_RE.search(line):
        return "unsafe"
    if DOSE_LINE_RE.search(line):
        return "dose"
    if DISCLAIMER_LIKE_RE.search(line):
        return "disclaimer"
    return None


def sanitize_answer(text: str, question: str) -> str:
    """Bản dùng cho chế độ không phát dần: lọc dòng không an toàn."""
    lines = text.split("\n")
    dose_dropped = any(drop_reason(ln) == "dose" for ln in lines)
    text = "\n".join(ln for ln in lines if drop_reason(ln) is None).strip()
    if "co giật" in (question + " " + text).lower() and "vào miệng" not in text:
        text += "\n" + SEIZURE_NOTE
    if dose_dropped:
        text += "\n" + DOSE_NOTE
    return text


@dataclass
class Answer:
    text: str
    allowed: bool
    topic: TopicResult | None = None
    entities: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    timings: dict = field(default_factory=dict)


class MedicalChatbot:
    def __init__(self):
        self.topic = TopicFilter()
        self.embedder = self.topic.embedder
        self.collection = self.topic.collection  # hỏi đáp ViHealthQA (cũng dùng cho bộ lọc chủ đề)
        self.encyc = None  # bài viết y khoa ViMedAQA, có thể chưa nạp
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            self.encyc = client.get_collection(f"{COLLECTION}_vimedaqa")
        except Exception:
            self.encyc = None

    def warmup(self):
        """Nạp sẵn NER và qwen để các câu hỏi sau không phải chờ nạp mô hình."""
        extract_entities("đau đầu")
        ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            think=False,
            keep_alive=KEEP_ALIVE,
            options={"num_predict": 1},
        )

    @staticmethod
    def _query(col, emb, n: int) -> list:
        res = col.query(
            query_embeddings=emb,
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            title = meta.get("question", "")
            kw = meta.get("keyword", "")
            if kw and kw.lower() not in title.lower():
                title = f"{kw} - {title}"
            out.append({
                "text": doc[:MAX_DOC_CHARS],
                "question": title,
                "link": meta.get("link", ""),
                "distance": dist,
                "source": meta.get("source", ""),
            })
        return out

    def retrieve(self, question: str, entities: list, use_entities: bool = True) -> list:
        query = question
        if use_entities and entities:
            query += " " + " ".join(dict.fromkeys(e["text"] for e in entities))
        emb = self.embedder.encode(
            [f"query: {query}"], normalize_embeddings=True
        ).tolist()
        docs = []
        if self.encyc is not None:
            docs += self._query(self.encyc, emb, QUOTA_ENCYC)
            docs += self._query(self.collection, emb, QUOTA_QA)
        else:
            docs += self._query(self.collection, emb, TOP_K)
        return docs

    @staticmethod
    def _dedupe_sources(docs: list) -> list:
        sources, seen = [], set()
        for d in docs:
            key = d["link"] or d["question"]
            if key not in seen:
                seen.add(key)
                sources.append(d)
        return sources

    def _chat_stream(self, question: str, entities: list, docs: list):
        """Sinh ra các cặp ("token", chuỗi) và cuối cùng ("stats", dict)."""
        ctx = "\n\n".join(f"[{i}] {d['text']}" for i, d in enumerate(docs, 1))
        ent = ", ".join(f"{e['text']} ({e['label']})" for e in entities) or "không có"
        user = (
            f"Thực thể y tế nhận diện: {ent}\n\n"
            f"TÀI LIỆU THAM KHẢO:\n{ctx}\n\n"
            f"CÂU HỎI: {question}"
        )
        stream = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            think=False,
            stream=True,
            keep_alive=KEEP_ALIVE,
            options={"temperature": 0.2, "num_ctx": 4096, "num_predict": MAX_NEW_TOKENS},
        )
        stats = {}
        for chunk in stream:
            piece = chunk["message"]["content"]
            if piece:
                yield "token", piece
            if getattr(chunk, "done", False):
                stats = {
                    "prompt_tokens": getattr(chunk, "prompt_eval_count", None),
                    "gen_tokens": getattr(chunk, "eval_count", None),
                    "prompt_s": round((getattr(chunk, "prompt_eval_duration", 0) or 0) / 1e9, 1),
                    "gen_s": round((getattr(chunk, "eval_duration", 0) or 0) / 1e9, 1),
                }
        yield "stats", stats

    def generate(self, question: str, entities: list, docs: list):
        text, stats = "", {}
        for kind, val in self._chat_stream(question, entities, docs):
            if kind == "token":
                text += val
            else:
                stats = val
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = "\n".join(ln for ln in text.split("\n") if not DISCLAIMER_LIKE_RE.search(ln))
        return text.strip(), stats

    def ask(self, question: str, use_entities: bool = True) -> Answer:
        question = question.strip()[:MAX_QUESTION_CHARS]
        if not question:
            return Answer("Bạn hãy nhập câu hỏi về sức khoẻ nhé.", allowed=False)

        timings = {}

        def timed(name, fn, *args, **kwargs):
            t0 = time.perf_counter()
            out = fn(*args, **kwargs)
            timings[name] = round((time.perf_counter() - t0) * 1000)
            return out

        topic = timed("loc_chu_de", self.topic.check, question)
        if not topic.allowed:
            return Answer(REFUSAL, False, topic, timings=timings)

        entities = timed("ner", extract_entities, question)
        prefix = EMERGENCY + "\n\n" if RED_FLAG_RE.search(question) else ""

        if DOSE_RE.search(question):
            timings["nhanh"] = "cau hoi ve lieu, khong goi qwen"
            return Answer(prefix + DOSE_REPLY, True, topic, entities, [], timings)

        docs = timed("truy_xuat", self.retrieve, question, entities, use_entities)

        try:
            text, stats = timed("qwen", self.generate, question, entities, docs)
            text = sanitize_answer(text, question)
            timings["qwen_chi_tiet"] = stats
        except Exception as e:
            text = f"Xin lỗi, hệ thống đang gặp sự cố khi tạo câu trả lời ({type(e).__name__})."
            return Answer(prefix + text, True, topic, entities, docs, timings)

        return Answer(
            f"{prefix}{text}\n\n{DISCLAIMER}", True, topic, entities,
            self._dedupe_sources(docs), timings,
        )

    def ask_stream(self, question: str, use_entities: bool = True):
        """Sinh ra các sự kiện:
        meta (chủ đề, thực thể), static (văn bản cố định, hiển thị ngay),
        text (một dòng đã lọc của qwen), final (nguồn, thống kê)."""
        question = question.strip()[:MAX_QUESTION_CHARS]
        if not question:
            yield {"type": "static", "text": "Bạn hãy nhập câu hỏi về sức khoẻ nhé."}
            yield {"type": "final", "allowed": False, "sources": [], "stats": {}}
            return

        topic = self.topic.check(question)
        if not topic.allowed:
            yield {"type": "static", "text": REFUSAL}
            yield {"type": "final", "allowed": False, "sources": [], "stats": {},
                   "topic": topic}
            return

        entities = extract_entities(question)
        yield {"type": "meta", "topic": topic, "entities": entities}

        if RED_FLAG_RE.search(question):
            yield {"type": "static", "text": EMERGENCY + "\n\n"}

        if DOSE_RE.search(question):
            yield {"type": "static", "text": DOSE_REPLY}
            yield {"type": "final", "allowed": True, "sources": [], "stats": {}}
            return

        docs = self.retrieve(question, entities, use_entities)

        emitted, buf, stats, dose_dropped = "", "", {}, False
        try:
            for kind, val in self._chat_stream(question, entities, docs):
                if kind == "token":
                    buf += val
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        reason = drop_reason(line)
                        if reason == "dose":
                            dose_dropped = True
                        if reason is None:
                            emitted += line + "\n"
                            yield {"type": "text", "text": line + "\n"}
                else:
                    stats = val
            if buf:
                reason = drop_reason(buf)
                if reason == "dose":
                    dose_dropped = True
                if reason is None:
                    emitted += buf
                    yield {"type": "text", "text": buf}
        except Exception as e:
            yield {"type": "static",
                   "text": f"\n\nXin lỗi, hệ thống gặp sự cố khi tạo câu trả lời ({type(e).__name__})."}

        if "co giật" in (question + " " + emitted).lower() and "vào miệng" not in emitted:
            yield {"type": "static", "text": "\n" + SEIZURE_NOTE}
        if dose_dropped:
            yield {"type": "static", "text": "\n" + DOSE_NOTE}
        yield {"type": "static", "text": "\n\n" + DISCLAIMER}
        yield {"type": "final", "allowed": True, "stats": stats,
               "sources": self._dedupe_sources(docs)}