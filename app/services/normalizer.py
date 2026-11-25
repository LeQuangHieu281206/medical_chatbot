"""Chuẩn hoá câu hỏi: mở rộng teencode, khôi phục dấu tiếng Việt (bigram + Viterbi)."""
import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB_PATH = ROOT / "data/processed/kb.jsonl"
LEX_PATH = ROOT / "data/processed/diacritics_lexicon.json"
ABBREV_PATH = ROOT / "data/processed/abbrev_vi.csv"
ABBREV_EXT_PATH = ROOT / "data/processed/abbrev_yte_mo_rong.csv"
TEENCODE_PATH = ROOT / "data/processed/teencode_vi.csv"
CONF_PATH = ROOT / "data/processed/confusion_vi.csv"
CORPUS_DIR = ROOT / "data/corpus"      # corpus văn bản thật (fineweb-2 + wikipedia)
KB_WEIGHT = 12                           # nhân trọng số KB y tế (đo được w=12 là tối ưu)

WORD_RE = re.compile(r"\w+", re.UNICODE)
VN_MARKS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")

MIN_BIGRAM = 2           # bỏ các cặp xuất hiện 1 lần để file nhỏ, nạp nhanh
MAX_FORMS = 8            # số dạng có dấu tối đa cho mỗi âm tiết không dấu
LAMBDA = 0.8             # trọng số bigram so với unigram
ACCENT_RATIO_MIN = 0.25  # dưới ngưỡng này mới coi là câu thiếu dấu

# --- sửa lỗi chính tả trên từ đã có dấu ---
KEEP_RARE = 500       # từ có dấu xuất hiện >= ngưỡng này thì luôn giữ nguyên
TYPO_RATIO = 40       # dạng khác phải phổ biến gấp >= 40 lần mới thay
TYPO_MIN_ALT = 200    # ... và bản thân nó phải đủ phổ biến
TYPO_MIN_LEN = 4      # không sửa từ ngắn hơn 4 ký tự (dễ đụng tên riêng)
TYPO_GAIN = 1.0       # điểm bigram phải tốt hơn ít nhất ngần này (nats) mới thay

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

# Đơn vị đo: giữ nguyên, không mở rộng ("500 mg" -> "500 miligam" là nhiễu,
# và các khoá như "mmol/l" không thể khớp vì WORD_RE cắt tại "/")
UNIT_KEYS = frozenset("mg mcg ug ml mmhg iu bpm kg cm".split())
ALONE_RE = re.compile(r"\s*\(chỉ khi đứng một mình\)\s*", re.I)
# Guard bổ sung cho đại từ dễ đụng danh từ y khoa (tui ~ túi mật)
EXTRA_GUARD = {
    "tui": frozenset("mat thua mo nguc tiet trang minh phi day".split()),
}
# Một khoá teencode bị coi là "bị che khuất" khi có dạng có dấu khác đạt ít
# nhất ngưỡng này so với tần suất của nghĩa teencode
SHADOW_RATIO = 0.04
# Sửa cứng: từ sai không tồn tại trong tiếng Việt (khng, bệnnh) và xuất hiện
# trong lexicon ít hơn ngưỡng này thì thay luôn, không cần ngữ cảnh
HARD_MAX = 3
# Bảo vệ từ đã đúng: không cho bộ sửa lỗi đổi nó sang từ dễ nhầm khác
CONF_PROTECT = True
NUM_UNIT_RE = re.compile(r"(\d)(thang|tháng|tuoi|tuổi|ngay|ngày|tuan|tuần)(?![^\W\d_])", re.I)
UNIT_NUM_RE = re.compile(r"(thang|tháng|ngay|ngày)(\d)", re.I)


def strip_diacritics(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", text)


def has_marks(word: str) -> bool:
    return any(c in VN_MARKS for c in word.lower())


# --- tên thuốc: danh mục để sửa lỗi gõ + nhận diện tên đã đúng ---
DRUG_NAMES = ROOT / "data/processed/drug_names.json"   # scripts/build_drug_names.py
DRUG_INDEX = ROOT / "data/sources/duocthu/index.jsonl"
DRUG_KB = ROOT / "data/processed/kb_drugs_full.jsonl"
DRUG_NAME_RES = [
    r"^(.+?) được chỉ định trong những trường hợp nào\?$",
    r"^Ai không nên dùng (.+?)\?$",
    r"^Cần thận trọng khi dùng (.+?) ở những ai\?$",
    r"^Tác dụng phụ thường gặp của (.+?) là gì\?$",
    r"^(.+?) tương tác với những thuốc nào\?$",
]
# Mảnh tên chung chung, tách ra từ tên ghép thì không dùng làm tên thuốc
DRUG_NAME_STOP = frozenset({
    "acid", "dang", "dùng", "muoi", "muối", "dung", "dịch", "vien", "viên",
    "thuoc", "thuốc", "thuong", "thường", "khang", "kháng", "boi", "bôi",
    "uong", "uống", "sinh", "ngay", "ngày",
})


def load_drug_names() -> list[str]:
    """Tên thuốc (đã bỏ dấu) để sửa lỗi gõ.

    Ưu tiên `data/processed/drug_names.json` (Dược thư + tên bổ sung từ KB,
    dựng bằng scripts/build_drug_names.py); không có thì đọc thẳng index Dược
    thư, cuối cùng mới suy ra từ câu hỏi trong KB thuốc.
    """
    names = []
    if DRUG_NAMES.exists():
        names = json.loads(DRUG_NAMES.read_text(encoding="utf-8")).get("names", [])
    if not names and DRUG_INDEX.exists():
        with DRUG_INDEX.open(encoding="utf-8") as f:
            names = [json.loads(l).get("name", "") for l in f if l.strip()]
    if not names and DRUG_KB.exists():
        with DRUG_KB.open(encoding="utf-8") as f:
            for line in f:
                q = json.loads(line).get("question", "")
                for rx in DRUG_NAME_RES:
                    m = re.match(rx, q)
                    if m:
                        names.append(m.group(1))
                        break
    out = []
    for n in names:
        key = strip_diacritics(n.lower())
        # bỏ phần trong ngoặc: đó là mô tả ("Tretinoin (thuốc bôi)"), tách ra sẽ
        # sinh "tên thuốc" giả là "thuoc"/"boi"
        key = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", key)
        # "Epinephrin (adrenalin)", "Amoxicilin + acid clavulanic": tách thành
        # từng tên, để lỗi gõ ở phần nào cũng sửa được
        for part in re.split(r"[^a-z]+", key):
            if len(part) >= 5 and part not in DRUG_NAME_STOP:
                out.append(part)
    return sorted(set(out))


def edits_within(a: str, b: str, maxd: int) -> int:
    """Khoảng cách Damerau-Levenshtein (đảo 2 ký tự cạnh nhau tính 1), cắt sớm.

    Đảo chữ là kiểu gõ sai rất hay gặp ("acabrose" -> "acarbose") và
    Levenshtein thuần tính nó là 2, vượt ngưỡng nên không sửa được.
    """
    if abs(len(a) - len(b)) > maxd:
        return maxd + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != b[j - 1]))
            if prev2 is not None and j >= 2 and ca == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > maxd:
            return maxd + 1
        prev2, prev = prev, cur
    return prev[-1]


def _scan_text(text: str, uni: Counter, bi: Counter, weight: int = 1) -> None:
    """Cộng dồn unigram/bigram của một khối văn bản vào hai Counter."""
    text = unicodedata.normalize("NFC", text).lower()
    for sent in re.split(r"[.!?;\n]+", text):
        words = WORD_RE.findall(sent)
        if not words:
            continue
        uni["<s>"] += weight
        prev = "<s>"
        for w in words:
            tok = w if w.isalpha() else "<num>"
            uni[tok] += weight
            bi[(prev, tok)] += weight
            prev = tok


def _count_words(text: str, cnt: Counter) -> None:
    """Đếm unigram của văn bản thường (không nhân trọng số KB)."""
    for w in WORD_RE.findall(unicodedata.normalize("NFC", text).lower()):
        if w.isalpha():
            cnt[w] += 1


def build_lexicon(kb_path: Path = KB_PATH, out_path: Path = LEX_PATH,
                  corpus_dirs=(), kb_weight: int = KB_WEIGHT) -> None:
    """Dựng lexicon từ KB y tế + các file corpus_*.txt (mỗi dòng một câu).

    `gen` là tần suất **chỉ tính trên văn bản thường**, dùng để biết một chuỗi
    viết tắt (covid, hp, ast...) đã là từ thật trong tiếng Việt hay chưa: nếu
    đã phổ biến thì KHÔNG mở rộng, tránh "covid" -> "bệnh covid-19".
    """
    uni, bi, gen = Counter(), Counter(), Counter()

    if kb_path.exists():
        with kb_path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                for key in ("question", "answer"):
                    _scan_text(str(row.get(key, "")), uni, bi, kb_weight)

    for d in corpus_dirs:
        d = Path(d)
        if not d.exists():
            continue
        for path in sorted(d.glob("corpus_*.txt")):
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if len(line) > 10:
                        _scan_text(line, uni, bi, 1)
                        _count_words(line, gen)

    forms = defaultdict(list)
    for tok, n in uni.items():
        if tok.isalpha():
            forms[strip_diacritics(tok)].append((n, tok))
    forms = {k: [t for _, t in sorted(v, reverse=True)[:MAX_FORMS]] for k, v in forms.items()}

    data = {
        "uni": dict(uni),
        "bi": {f"{a}\t{b}": n for (a, b), n in bi.items() if n >= MIN_BIGRAM},
        "forms": forms,
        "gen": dict(gen),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class QueryNormalizer:
    def __init__(self, rebuild: bool = False):
        if rebuild or not LEX_PATH.exists():
            build_lexicon(corpus_dirs=(CORPUS_DIR,))
        data = json.loads(LEX_PATH.read_text(encoding="utf-8"))
        self.uni = data["uni"]
        self.bi = data["bi"]
        self.forms = data["forms"]
        self.gen = data.get("gen", {})
        self.total = sum(self.uni.values())
        self.vocab = len(self.uni)
        self.teen, self.teen_guard, self.teen_alone, self.teen_soft = self._load_teen()
        self.conf_cands, self.conf_protect, self.conf_hard = self._load_conf()
        # gộp tên cơ quan từ CSV với danh sách có sẵn để nhận "K dạ dày"
        self._cancer_next = frozenset(CANCER_NEXT) | self.teen_guard.get("k", frozenset())
        # chỉ mục (ký tự đầu, độ dài) -> các khoá không dấu, để tra mờ rẻ
        self._by_head = defaultdict(list)
        for key in self.forms:
            if key.isalpha():
                self._by_head[(key[0], len(key))].append(key)

        # tên thuốc: dùng để sửa lỗi gõ mà ngưỡng tần suất không bao giờ cho qua
        # (tên thuốc hiếm, TYPO_MIN_ALT=200 nên bộ tra mờ thường không đề xuất)
        self._drug_names = load_drug_names()
        self._drug_set = frozenset(self._drug_names)

    # ---- viết tắt / teencode ----
    @staticmethod
    def _load_teen():
        """Nạp 2 bảng CSV: viết tắt y tế + teencode.

        Trả về (rep, guard, alone):
          rep[k]   -> cụm đầy đủ
          guard[k] -> tập từ đứng cạnh mà nếu gặp thì KHÔNG mở rộng
          alone    -> tập khoá chỉ mở rộng khi câu không dấu (chống sửa oan)
        """
        rep, guard, alone = {}, {}, set()
        soft = set()          # khoá đến từ teencode (không phải viết tắt y tế)

        if ABBREV_PATH.exists():
            with ABBREV_PATH.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    QueryNormalizer._add_abbrev(row, rep, guard, "")

        if ABBREV_EXT_PATH.exists():
            with ABBREV_EXT_PATH.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    QueryNormalizer._add_abbrev(row, rep, guard, row.get("bien_the_go") or "")

        if TEENCODE_PATH.exists():
            with TEENCODE_PATH.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    k = unicodedata.normalize("NFC", row.get("teencode") or "").strip().lower()
                    v = unicodedata.normalize("NFC", row.get("nghia") or "").strip()
                    if not k or not v or "/" in k or " " in k or k in UNIT_KEYS:
                        continue
                    if ALONE_RE.search(v):
                        alone.add(k)
                        v = ALONE_RE.sub("", v)
                    v = v.lower()
                    if not v:
                        continue
                    keys = [k]
                    for alias in (row.get("bien_the_go") or "").split("|"):
                        a = unicodedata.normalize("NFC", alias).strip().lower()
                        if a and a != k and " " not in a and "/" not in a:
                            keys.append(a)
                    g = unicodedata.normalize("NFC", row.get("khong_mo_rong") or "").strip()
                    gset = frozenset(strip_diacritics(t.strip().lower()).split()[0]
                                     for t in g.split("|") if t.strip()) if g else None
                    for key in keys:
                        if gset:                # guard áp cả khi khoá đã có sẵn
                            guard[key] = guard.get(key, frozenset()) | gset
                        if key in rep:          # viết tắt y tế đã có thì giữ
                            continue
                        rep[key] = v
                        soft.add(key)

        # dự phòng: giữ từ điển cũ nếu thiếu CSV
        for k, v in TEEN.items():
            if k not in rep:
                rep[k] = v
                soft.add(k)
        for k, g in EXTRA_GUARD.items():
            guard[k] = guard.get(k, frozenset()) | g
        return rep, guard, alone, frozenset(soft)

    @staticmethod
    def _add_abbrev(row, rep, guard, variants):
        """Đăng ký một dòng viết tắt và các biến thể gõ của nó."""
        def N(s):
            return unicodedata.normalize("NFC", s or "").strip().lower()

        k, v = N(row.get("viet_tat")), N(row.get("day_du"))
        if not k or not v or "/" in k or k in UNIT_KEYS:
            return
        keys = [k]
        for alias in (variants or "").split("|"):
            a = N(alias)
            # biến thể có dấu cách hoặc "/" không khớp được một token
            if a and a != k and " " not in a and "/" not in a:
                keys.append(a)
        g = N(row.get("khong_mo_rong"))
        gset = frozenset(strip_diacritics(t.strip().lower()).split()[0]
                         for t in g.split("|") if t.strip()) if g else None
        for key in keys:
            rep.setdefault(key, v)
            if gset:
                guard[key] = gset

    def _load_conf(self):
        """Nạp bảng cặp từ dễ nhầm.

        Trả về (cands, protect, hard):
          cands[k]  -> các dạng đúng ứng viên cho k
          protect   -> từ đã đúng, không cho bộ sửa lỗi đổi đi
          hard[k]   -> dạng đúng chắc chắn (k không phải từ tiếng Việt)
        """
        cands, protect = defaultdict(list), set()
        pairs = defaultdict(set)
        if CONF_PATH.exists():
            with CONF_PATH.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    s = unicodedata.normalize("NFC", row.get("sai") or "").strip().lower()
                    d = unicodedata.normalize("NFC", row.get("dung") or "").strip().lower()
                    if not s or not d or s == d:
                        continue
                    pairs[s].add(d)
                    if (row.get("ca_hai_deu_la_tu_that") or "").strip() == "1":
                        protect.add(d)
        for s, ds in pairs.items():
            cands[s] = sorted(ds)
        # chỉ sửa cứng khi ánh xạ một chiều
        hard = {s: ds[0] for s, ds in cands.items() if len(ds) == 1}
        hard = {s: d for s, d in hard.items() if s not in protect}
        return cands, frozenset(protect), hard

    def expand_teencode(self, text: str, accented: bool = True) -> str:
        text = NUM_UNIT_RE.sub(r"\1 \2", text)    # 6thang -> 6 thang
        text = UNIT_NUM_RE.sub(r"\1 \2", text)    # tháng20 -> tháng 20
        ms = list(WORD_RE.finditer(text))
        out, last = [], 0
        for i, m in enumerate(ms):
            w = m.group(0)
            lw = w.lower()
            prev = ms[i - 1].group(0).lower() if i else ""
            nxt = ms[i + 1].group(0).lower() if i + 1 < len(ms) else ""
            nxt_d = strip_diacritics(nxt)
            prev_d = strip_diacritics(prev)
            prev2_d = strip_diacritics(ms[i - 2].group(0).lower()) if i >= 2 else ""
            rep = self._expand_one(lw, prev, prev_d, nxt, nxt_d, accented, prev2_d)
            if rep and w[0].isupper() and not w.isupper():
                rep = rep.capitalize()
            out.append(text[last:m.start()])
            out.append(rep or w)
            last = m.end()
        out.append(text[last:])
        return "".join(out)

    def _shadowed(self, key: str, target: str) -> bool:
        """Khoá trùng âm tiết thật có tần suất đáng kể thì để Viterbi quyết.

        "bit" -> "biết" an toàn (bít rất hiếm), nhưng "thuoc" không nên ép
        thành "thuốc" vì "kích thước"/"thuộc" cũng phổ biến. Với viết tắt y tế
        phần mở rộng là cả cụm ("va" -> "viêm vòm họng"): so theo từ ĐẦU của
        cụm, vì trước đây tần suất cụm bằng 0 nên mọi khoá đều lọt qua và
        "và" bị đổi thành "viêm vòm họng".
        """
        if not key.isalpha():
            return False
        first = target.split()[0] if target else ""
        t = self.uni.get(first, 0)
        if t <= 0:
            return False
        coll = sum(self.uni.get(f, 0)
                   for f in self.forms.get(key, ())
                   if f != key and f != target and has_marks(f))
        return coll >= SHADOW_RATIO * t

    def _expand_one(self, lw, prev, prev_d, nxt, nxt_d, accented, prev2_d=""):
        """Quyết định mở rộng một token (đã lowercase).

        `accented` hiện không dùng để chặn, vì việc chặn đã do `teen_alone`
        và bộ khôi phục dấu đảm nhiệm; giữ tham số cho tương thích lời gọi.
        """
        # "k" có 2 nghĩa: đứng trước tên cơ quan là ung thư, còn lại là không
        if lw in self._drug_set:
            return None   # tên thuốc đã đúng: không đổi thành cụm mô tả
        if lw == "k":
            if nxt_d in self._cancer_next:
                return "ung thư"
            if prev_d in NO_SINGLE_AFTER or nxt_d in NO_SINGLE_AFTER:
                return None
            return None if accented else "không"

        if lw in self.teen and lw not in self.teen_alone:
            if prev_d.isdigit():
                return None           # "2 nm", "3 xn": gần như chắc là số đếm
            exp = self.teen[lw]
            if " " in exp:
                words = WORD_RE.findall(exp)
                # (1) cụm mở rộng chỉ là khoá + từ chung ("ast" -> "men gan ast",
                #     "covid" -> "bệnh covid-19"): viết lại chẳng thêm thông tin
                if lw in words:
                    return None
                # (2) tránh lặp từ vừa xuất hiện: "vi khuẩn hp" không được thành
                #     "vi khuẩn vi khuẩn helicobacter pylori"
                if {prev_d, prev2_d} & {w for w in words if len(w) > 1}:
                    return None
            g = self.teen_guard.get(lw)
            if g and (nxt_d in g or prev_d in g):
                return None
            # Mọi khoá đều phải qua luật che khuất: "a" trùng "ạ", "cho" trùng
            # "chợ/chờ", "va" trùng "và" — gặp là để Viterbi tự quyết theo ngữ cảnh
            if self._shadowed(lw, exp):
                return None
            return self.teen[lw]

        # Khoá "chỉ khi đứng một mình" (dau, hieu, chua, a...) trùng với âm
        # tiết thật khi bỏ dấu, nên để bộ khôi phục dấu quyết định; nhưng các
        # chữ cái đơn j/r/z/k vẫn đi qua SINGLE.
        if lw in SINGLE and prev not in NO_SINGLE_AFTER and prev_d not in NO_SINGLE_AFTER:
            return SINGLE[lw]
        return None

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

    # ---- sửa lỗi chính tả ----
    @staticmethod
    def _edit_le1(a: str, b: str) -> bool:
        """Hai xâu cách nhau tối đa 1 phép chèn/xoá/thay/đảo 2 ký tự kề."""
        if a == b:
            return True
        if len(a) == len(b):
            diff = [i for i in range(len(a)) if a[i] != b[i]]
            if len(diff) == 1:
                return True
            return (len(diff) == 2 and diff[1] == diff[0] + 1
                    and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
        if abs(len(a) - len(b)) > 1:
            return False
        if len(a) > len(b):
            a, b = b, a
        i = 0
        while i < len(a) and a[i] == b[i]:
            i += 1
        return a[i:] == b[i + 1:]

    def _fuzzy_keys(self, key: str) -> list:
        n = len(key)
        out = []
        for size in (n - 1, n, n + 1):
            for k in self._by_head.get((key[0], size), ()):
                if self._edit_le1(key, k):
                    out.append(k)
        return out

    def _typo_cands(self, word: str, allow_fuzzy: bool = True) -> list:
        """Ứng viên cho từ gõ sai: cùng âm tiết không dấu, hoặc lệch 1 ký tự."""
        key = strip_diacritics(word.lower())
        if not key.isalpha():
            return []
        scored = {f: self.uni.get(f, 0) for f in self.forms.get(key, ())}
        # tra mờ chỉ khi âm tiết gốc không có trong từ điển (sai/chèn/xoá chữ cái)
        if allow_fuzzy and len(key) >= TYPO_MIN_LEN:
            for k in self._fuzzy_keys(key):
                for f in self.forms[k]:
                    n = self.uni.get(f, 0)
                    if n >= TYPO_MIN_ALT:      # khoá rác xuất hiện 1-2 lần thì bỏ
                        scored[f] = max(scored.get(f, 0), n)
        best = sorted(((n, f) for f, n in scored.items() if n),
                      key=lambda x: (-x[0], x[1]))
        return [f for _, f in best[:MAX_FORMS]]

    def _drug_cand(self, word: str) -> str | None:
        """Sửa tên thuốc gõ sai (nuốt chữ, gõ đôi, đảo chữ, đọc chệch).

        Chỉ nhận khi:
          - từ hiện tại không phải từ tiếng Việt phổ biến (nếu không sẽ đè lên từ thật)
          - có đúng MỘT tên thuốc gần nhất theo khoảng cách sửa (tránh đoán bừa)
        """
        key = strip_diacritics(word.lower())
        if not key.isalpha() or len(key) < 5:
            return None
        if key in self._drug_set:
            return key
        if self.uni.get(key, 0) >= KEEP_RARE:   # từ đủ phổ biến, không phải lỗi gõ
            return None
        maxd = 1 if len(key) < 9 else 2
        best = []
        for name in self._drug_names:
            d = edits_within(key, name, maxd)
            if d <= maxd:
                best.append((d, self.uni.get(name, 0), name))
        if not best:
            return None
        best.sort(key=lambda x: (x[0], -x[1], x[2]))
        if len(best) > 1 and best[1][0] == best[0][0]:
            # Hai tên cùng gần: nếu chỉ là hai cách viết của cùng một chất
            # (amoxicilin / amoxicillin) thì lấy cách viết phổ biến hơn,
            # khác chất thật thì không được đoán.
            if edits_within(best[0][2], best[1][2], 1) > 1:
                return None
        # Chính tả sai của người khác cũng được đếm vào `uni` ("paracetamon" có
        # 74 lần trong KB), nên không dùng ngưỡng tuyệt đối mà dùng tỉ lệ: tên
        # đúng phải phổ biến hơn hẳn cách gõ sai.
        if self.uni.get(best[0][2], 0) < 5 * self.uni.get(key, 0):
            return None
        return best[0][2]

    def _cands(self, w: str, allow_unmarked: bool = True) -> list:
        if not w.isalpha():
            return [w]
        lw = w.lower()
        # từ sai không tồn tại trong tiếng Việt: thay luôn, không cần ngữ cảnh
        h = self.conf_hard.get(lw)
        if h and self.uni.get(lw, 0) <= HARD_MAX:
            return [h]
        d = self._drug_cand(lw)
        if d and d != lw:
            return [d]
        if has_marks(lw):
            # từ có dấu, phổ biến -> tin luôn; hiếm/lạ -> chỉ nhận dạng áp đảo
            if self.uni.get(lw, 0) >= KEEP_RARE:
                return [lw]
            key = strip_diacritics(lw)
            cands = [c for c in self._typo_cands(lw, allow_fuzzy=key not in self.forms)
                     if self._is_typo(lw, c)]
            for c in self.conf_cands.get(lw, ()):
                if c not in cands:
                    cands.append(c)
            return cands or [lw]
        if not allow_unmarked:
            return [lw]
        if lw in self.forms:
            # từ không dấu trùng một dạng có thật không có nghĩa là đúng:
            # "bit" có trong forms nhưng "biết" (khoá "biet") mới là đích.
            # Chỉ thêm ứng viên tra mờ khi nó phổ biến ÁP ĐẢO, nếu không sẽ
            # sinh lỗi ngược (truoc -> thuốc).
            base = self.forms[lw]
            top = max((self.uni.get(f, 0) for f in base), default=0)
            extra = [f for f in self._typo_cands(lw, allow_fuzzy=True)
                     if self.uni.get(f, 0) >= TYPO_RATIO * max(top, 1)]
            extra += [c for c in self.conf_cands.get(lw, ()) if c not in extra]
            return list(dict.fromkeys(list(base) + extra))
        cands = self._typo_cands(lw)
        cands += [c for c in self.conf_cands.get(lw, ()) if c not in cands]
        return [c for c in cands if self.uni.get(c, 0) >= TYPO_MIN_ALT] or [lw]

    def _is_typo(self, word: str, repl: str) -> bool:
        """Chỉ thay khi dạng mới áp đảo hẳn, tránh đụng từ hiếm nhưng đúng."""
        if repl == word.lower():
            return False
        cur = self.uni.get(word.lower(), 0)
        if cur >= KEEP_RARE:
            return False
        # từ nằm trong bảng "cả hai đều là từ thật" thì không được đổi đi:
        # đây là cặp dễ nhầm (mười/muối, tám/tâm), từ điển không đủ tin
        if CONF_PROTECT and word.lower() in self.conf_protect:
            return False
        alt = self.uni.get(repl, 0)
        return alt >= TYPO_MIN_ALT and alt >= TYPO_RATIO * max(cur, 1)

    def _accept_typo(self, seq: list, i: int, word: str, repl: str) -> bool:
        """Đồng ý thay từ hiếm bằng dạng phổ biến khi ngữ cảnh cũng ủng hộ."""
        if not self._is_typo(word, repl):
            return False
        ctx = lambda t: t if t.isalpha() else "<num>"
        prev = ctx(seq[i - 1]) if i else "<s>"
        nxt = ctx(seq[i + 1]) if i + 1 < len(seq) else "</s>"
        gain = (self._logp(prev, ctx(repl)) + self._logp(ctx(repl), nxt)
                - self._logp(prev, ctx(word.lower())) - self._logp(ctx(word.lower()), nxt))
        return gain >= TYPO_GAIN

    def restore_diacritics(self, text: str, allow_unmarked: bool = True) -> str:
        ms = list(WORD_RE.finditer(text))
        if not ms:
            return text
        words = [m.group(0) for m in ms]
        cands = [self._cands(w, allow_unmarked) for w in words]
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
        for i, (m, new) in enumerate(zip(ms, seq)):
            w = m.group(0)
            if w.isalpha() and new != w.lower():
                if has_marks(w) and not self._accept_typo(seq, i, w, new):
                    new = w
                elif w.isupper() and len(w) > 1:
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
        # luôn chạy: khôi phục dấu khi câu thiếu dấu, sửa chính tả khi câu đã có dấu
        text = self.restore_diacritics(text, allow_unmarked=not accented)
        return re.sub(r"\s+", " ", text)