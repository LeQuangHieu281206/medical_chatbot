"""Chuẩn hoá câu hỏi: mở rộng teencode, khôi phục dấu tiếng Việt (bigram + Viterbi)."""
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB_PATH = ROOT / "data/processed/kb.jsonl"
LEX_PATH = ROOT / "data/processed/diacritics_lexicon.json"

WORD_RE = re.compile(r"\w+", re.UNICODE)
VN_MARKS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")

MIN_BIGRAM = 2           # bỏ các cặp xuất hiện 1 lần để file nhỏ, nạp nhanh
MAX_FORMS = 8            # số dạng có dấu tối đa cho mỗi âm tiết không dấu
LAMBDA = 0.8             # trọng số bigram so với unigram
ACCENT_RATIO_MIN = 0.25  # dưới ngưỡng này mới coi là câu thiếu dấu

TEEN = {
    # viết tắt
    "ntn": "như thế nào", "bs": "bác sĩ", "bsi": "bác sĩ", "bv": "bệnh viện",
    "qh": "quan hệ", "kq": "kết quả", "xn": "xét nghiệm", "nc": "nước",
    "trc": "trước", "hnay": "hôm nay",
    # teencode, bỏ chữ cái, sai chính tả phổ biến
    "ko": "không", "hok": "không", "dc": "được", "đc": "được", "vs": "với",
    "mik": "mình", "mk": "mình", "fai": "phải", "pải": "phải",
    "nhg": "những", "nhưg": "nhưng", "nhug": "nhưng", "nhìu": "nhiều",
    "cũg": "cũng", "cug": "cũng", "nhiu": "nhiều", "bj": "bị", "bịnh": "bệnh",
    "đag": "đang", "thág": "tháng", "mún": "muốn", "khj": "khi", "ji": "gì",
    "sỉ": "sĩ", "tui": "tôi", "vacine": "vaccine", "vaxcin": "vaccine",
}
SINGLE = {"k": "không", "j": "gì", "z": "vậy", "r": "rồi"}   # chỉ khi gõ chữ thường
NO_SINGLE_AFTER = {"vitamin", "vit", "nhóm", "nhom", "type", "loại", "loai"}
# "k" đứng trước tên cơ quan thường là ung thư (K dạ dày), không mở rộng
CANCER_NEXT = {"dạ", "phổi", "gan", "vú", "tuyến", "đại", "vòm", "cổ", "tụy",
               "thận", "máu", "xương", "buồng", "tử"}
NUM_UNIT_RE = re.compile(r"(\d)(thang|tháng|tuoi|tuổi|ngay|ngày|tuan|tuần)(?![^\W\d_])", re.I)
UNIT_NUM_RE = re.compile(r"(thang|tháng|ngay|ngày)(\d)", re.I)


def strip_diacritics(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", text)


def has_marks(word: str) -> bool:
    return any(c in VN_MARKS for c in word.lower())


def build_lexicon(kb_path: Path = KB_PATH, out_path: Path = LEX_PATH) -> None:
    uni, bi = Counter(), Counter()
    with kb_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            for key in ("question", "answer"):
                text = unicodedata.normalize("NFC", str(row.get(key, ""))).lower()
                for sent in re.split(r"[.!?;\n]+", text):
                    words = WORD_RE.findall(sent)
                    if not words:
                        continue
                    uni["<s>"] += 1
                    prev = "<s>"
                    for w in words:
                        tok = w if w.isalpha() else "<num>"
                        uni[tok] += 1
                        bi[(prev, tok)] += 1
                        prev = tok

    forms = defaultdict(list)
    for tok, n in uni.items():
        if tok.isalpha():
            forms[strip_diacritics(tok)].append((n, tok))
    forms = {k: [t for _, t in sorted(v, reverse=True)[:MAX_FORMS]] for k, v in forms.items()}

    data = {
        "uni": dict(uni),
        "bi": {f"{a}\t{b}": n for (a, b), n in bi.items() if n >= MIN_BIGRAM},
        "forms": forms,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class QueryNormalizer:
    def __init__(self, rebuild: bool = False):
        if rebuild or not LEX_PATH.exists():
            build_lexicon()
        data = json.loads(LEX_PATH.read_text(encoding="utf-8"))
        self.uni = data["uni"]
        self.bi = data["bi"]
        self.forms = data["forms"]
        self.total = sum(self.uni.values())
        self.vocab = len(self.uni)

    # ---- teencode ----
    def expand_teencode(self, text: str, accented: bool = True) -> str:
        text = NUM_UNIT_RE.sub(r"\1 \2", text)    # 6thang -> 6 thang
        text = UNIT_NUM_RE.sub(r"\1 \2", text)    # tháng20 -> tháng 20
        ms = list(WORD_RE.finditer(text))
        out, last = [], 0
        for i, m in enumerate(ms):
            w = m.group(0)
            prev = ms[i - 1].group(0).lower() if i else ""
            nxt = ms[i + 1].group(0).lower() if i + 1 < len(ms) else ""
            rep = TEEN.get(w.lower())
            if rep and not accented and self._ambiguous(w.lower()):
                rep = None   # câu không dấu: để bộ khôi phục dấu quyết định
            if rep and w[0].isupper() and not w.isupper():
                rep = rep.capitalize()
            if rep is None and w in SINGLE and prev not in NO_SINGLE_AFTER:
                if not (w == "k" and nxt in CANCER_NEXT):
                    rep = SINGLE[w]
            out.append(text[last:m.start()])
            out.append(rep or w)
            last = m.end()
        out.append(text[last:])
        return "".join(out)

    def _ambiguous(self, key: str) -> bool:
        """Từ teencode trùng với âm tiết không dấu có thật (vd. tui ~ túi)."""
        k = self.uni.get(key, 0)
        return key.isascii() and any(
            f != key and has_marks(f) and f not in TEEN
            and self.uni.get(f, 0) >= max(10, 3 * k)
            for f in self.forms.get(key, []))

    # ---- phát hiện câu thiếu dấu ----
    def accent_ratio(self, text: str) -> float:
        toks = [w.lower() for w in WORD_RE.findall(text) if w.isalpha()]
        known = [w for w in toks if strip_diacritics(w) in self.forms]
        if len(known) < 2:
            return 1.0  # quá ngắn, không đụng vào
        return sum(has_marks(w) for w in known) / len(known)

    # ---- khôi phục dấu ----
    def _logp(self, prev: str, cur: str) -> float:
        u = (self.uni.get(cur, 0) + 0.1) / (self.total + 0.1 * self.vocab)
        pu = self.uni.get(prev, 0)
        b = self.bi.get(prev + "\t" + cur, 0)
        p = u if pu == 0 else LAMBDA * b / pu + (1 - LAMBDA) * u
        return math.log(p)

    def _cands(self, w: str) -> list:
        if not w.isalpha():
            return [w]
        lw = w.lower()
        if has_marks(lw):
            return [lw]
        return self.forms.get(lw) or [lw]

    def restore_diacritics(self, text: str) -> str:
        ms = list(WORD_RE.finditer(text))
        if not ms:
            return text
        words = [m.group(0) for m in ms]
        cands = [self._cands(w) for w in words]
        ctx = lambda t: t if t.isalpha() else "<num>"

        history = [{c: (self._logp("<s>", ctx(c)), None) for c in cands[0]}]
        for i in range(1, len(words)):
            layer = {}
            for c in cands[i]:
                best_prev, best_sc = None, -1e18
                for p, (sc, _) in history[-1].items():
                    s = sc + self._logp(ctx(p), ctx(c))
                    if s > best_sc:
                        best_sc, best_prev = s, p
                layer[c] = (best_sc, best_prev)
            history.append(layer)

        cur = max(history[-1], key=lambda c: history[-1][c][0])
        seq = [cur]
        for i in range(len(words) - 1, 0, -1):
            cur = history[i][cur][1]
            seq.append(cur)
        seq.reverse()

        out, last = [], 0
        for m, new in zip(ms, seq):
            w = m.group(0)
            if w.isalpha() and new != w.lower():
                if w.isupper() and len(w) > 1:
                    new = new.upper()
                elif w[0].isupper():
                    new = new[0].upper() + new[1:]
            else:
                new = w
            out.append(text[last:m.start()])
            out.append(new)
            last = m.end()
        out.append(text[last:])
        return "".join(out)

    def normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFC", text).strip()
        accented = self.accent_ratio(text) >= ACCENT_RATIO_MIN
        text = self.expand_teencode(text, accented)
        if not accented:
            text = self.restore_diacritics(text)
        return re.sub(r"\s+", " ", text)