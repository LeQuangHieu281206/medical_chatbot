"""Chẩn đoán riêng: nhận dạng viết tắt / teencode và sửa lỗi chính tả.

Khác với 38_eval_typo (chấm cả câu), file này tách từng năng lực:
  A. Viết tắt y tế + teencode: mở rộng được hay không (theo từng nhóm).
  B. Lỗi chính tả: chèn / xoá / thay / đảo ký tự / sai dấu thanh — độ chính xác theo loại.
  C. Câu sạch: có bị đổi oan không.
"""
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.normalizer import QueryNormalizer, WORD_RE, has_marks, strip_diacritics  # noqa: E402

RNG = random.Random(7)


def toks(t):
    return WORD_RE.findall(unicodedata.normalize("NFC", t).lower())


def norm_txt(s):
    return re.sub(r"\s+", " ", strip_diacritics(s.lower())).strip()


# ---------------------------------------------------------------- A. viết tắt
# (câu hỏi thô, dạng đúng mong đợi)
ABBREV = [
    # --- nhóm đã khai báo trong TEEN ---
    ("bs oi cho e hoi", "bác sĩ ơi cho em hỏi", "declared"),
    ("bv nao chua benh nay", "bệnh viện nào chữa bệnh này", "declared"),
    ("kq xn mau the nao", "kết quả xét nghiệm máu thế nào", "declared"),
    ("ntn la bi binh", "như thế nào là bị bệnh", "declared"),
    ("ko biet co sao ko", "không biết có sao không", "declared"),
    ("toi bi dc 2 nam", "tôi bị được 2 năm", "declared"),
    # --- viết tắt y tế KHÔNG khai báo (kỳ vọng: chưa xử lý) ---
    ("ha thap keo dai", "huyết áp thấp kéo dài", "undeclared"),
    ("tha do type 2", "tăng huyết áp do type 2", "undeclared"),
    ("dtd type 2 co bien chung", "đái tháo đường type 2 có biến chứng", "undeclared"),
    ("ut da day giai doan 2", "ung thư dạ dày giai đoạn 2", "undeclared"),
    ("nmct cap", "nhồi máu cơ tim cấp", "undeclared"),
    ("tbmmn o nguoi tre", "tai biến mạch máu não ở người trẻ", "undeclared"),
    ("sot xh dengue", "sốt xuất huyết dengue", "undeclared"),
    ("viem gtmn", "viêm giãn tĩnh mạch mạn tính", "undeclared"),
    ("ckd gd 3", "bệnh thận mạn giai đoạn 3", "undeclared"),
    ("mri so nao", "chụp cộng hưởng từ sọ não", "undeclared"),
    ("xn hbv dna", "xét nghiệm virus viêm gan b dna", "undeclared"),
    ("u gan kich thuoc 3cm", "khối u gan kích thước 3cm", "undeclared"),
    # --- teencode ---
    ("mik bi dau bung", "mình bị đau bụng", "teencode"),
    ("hok bit j ca", "không biết gì cả", "teencode"),
    ("nhug ma van dau", "nhưng mà vẫn đau", "teencode"),
    ("uog thuoc 2 tuan", "uống thuốc 2 tuần", "teencode"),
    ("bj sot 3 ngay", "bị sốt 3 ngày", "teencode"),
    ("bịnh nay nguy hiem ko", "bệnh này nguy hiểm không", "teencode"),
    ("tui mun hoi bs", "tôi muốn hỏi bác sĩ", "teencode"),
]

# ------------------------------------------------------------- B. loại lỗi
def typo_delete(w):
    if len(w) < 4:
        return None
    i = RNG.randrange(len(w) - 1) + 1
    return w[:i] + w[i + 1:]


def typo_insert(w):
    if len(w) < 3:
        return None
    i = RNG.randrange(len(w) - 1) + 1
    return w[:i] + w[i - 1] + w[i:]          # nhân đôi ký tự kề (viiên)


def typo_swap(w):
    if len(w) < 3:
        return None
    i = RNG.randrange(len(w) - 1)
    return w[:i] + w[i + 1] + w[i] + w[i + 2:]


def typo_subst(w):
    if len(w) < 3:
        return None
    i = RNG.randrange(len(w) - 1) + 1
    return w[:i] + RNG.choice("nhtcsmv") + w[i + 1:]


TONE_SWAP = {"á": "à", "à": "á", "ả": "ã", "ã": "ả", "ạ": "á",
             "é": "è", "è": "é", "ẻ": "ẽ", "ẽ": "ẻ", "ệ": "ề",
             "ó": "ò", "ò": "ó", "ỏ": "õ", "õ": "ỏ", "ọ": "ó",
             "ú": "ù", "ù": "ú", "ủ": "ũ", "ĩ": "í", "í": "ì",
             "ấ": "ầ", "ầ": "ấ", "ẩ": "ẫ", "ẫ": "ẩ",
             "ế": "ề", "ề": "ế", "ể": "ễ", "ễ": "ể",
             "ố": "ồ", "ồ": "ố", "ổ": "ỗ", "ỗ": "ổ",
             "ứ": "ừ", "ừ": "ứ", "ử": "ữ", "ữ": "ử",
             "ớ": "ờ", "ờ": "ớ", "ở": "ỡ", "ỡ": "ở"}


def typo_tone(w):
    pos = [i for i, c in enumerate(w) if c in TONE_SWAP]
    if not pos:
        return None
    i = RNG.choice(pos)
    return w[:i] + TONE_SWAP[w[i]] + w[i + 1:]


def typo_nodiac(w):
    if not has_marks(w):
        return None
    return strip_diacritics(w)


KINDS = [
    ("xoá ký tự", typo_delete),
    ("chèn ký tự", typo_insert),
    ("đảo ký tự", typo_swap),
    ("thay ký tự", typo_subst),
    ("sai dấu thanh", typo_tone),
    ("bỏ hết dấu", typo_nodiac),
]


def inject(sent, fn):
    """Áp lỗi lên 1 từ trong câu; trả về (câu lỗi, số từ bị đổi) hoặc None."""
    ms = list(WORD_RE.finditer(sent))
    idx = [i for i, m in enumerate(ms) if m.group(0).isalpha() and len(m.group(0)) >= 4]
    if not idx:
        return None
    i = RNG.choice(idx)
    m = ms[i]
    bad = fn(m.group(0))
    if not bad or bad == m.group(0):
        return None
    return sent[:m.start()] + bad + sent[m.end():]


def accuracy(norm, pairs):
    """pairs: [(native, gold)] -> % âm tiết đúng."""
    tot = ok = 0
    for noisy, gold in pairs:
        g, p = toks(gold), toks(norm.normalize(noisy))
        if len(g) != len(p):
            continue
        for a, b in zip(g, p):
            if a.isalpha():
                tot += 1
                ok += a == b
    return 100 * ok / max(tot, 1), tot


def main():
    norm = QueryNormalizer()
    print(f"Từ điển: {norm.vocab} token, {len(norm.forms)} âm tiết không dấu\n")

    # ---- A ----
    print("=" * 78)
    print("A. NHẬN DẠNG VIẾT TẮT / TEENCODE")
    print("=" * 78)
    by_group = {}
    for noisy, gold, group in ABBREV:
        out = norm.normalize(noisy)
        worked = norm_txt(out) == norm_txt(gold)
        by_group.setdefault(group, []).append(worked)
        flag = "OK  " if worked else "MISS"
        print(f"  {flag} [{group:<10}] {noisy:<26} -> {out}")
        if not worked:
            print(f"       {'':<12}  mong đợi: {gold}")
    print()
    for g, v in by_group.items():
        print(f"  {g:<12}: {sum(v)}/{len(v)} = {100*sum(v)/len(v):.0f}%")

    # ---- B ----
    print("\n" + "=" * 78)
    print("B. SỬA LỖI CHÍNH TẢ THEO LOẠI LỖI (câu đã có dấu)")
    print("=" * 78)
    rows = [json.loads(l) for l in (ROOT / "data/processed/eval.jsonl").open(encoding="utf-8") if l.strip()]
    sents = [r.get("question") or r.get("original") or "" for r in rows]
    sents = [s for s in sents if 20 < len(s) < 300][:400]

    print(f"  {'loại lỗi':<16}{'âm tiết%':>10}{'số âm tiết':>12}")
    for name, fn in KINDS:
        pairs = []
        for s in sents:
            bad = inject(s, fn)
            if bad:
                pairs.append((bad, s))
        acc, tot = accuracy(norm, pairs)
        print(f"  {name:<16}{acc:>10.2f}{tot:>12}")

    # ---- C ----
    print("\n" + "=" * 78)
    print("C. HỒI QUY TRÊN CÂU SẠCH (không được đổi từ nào)")
    print("=" * 78)
    changed = tot = 0
    ex = []
    for s in sents:
        o, p = toks(s), toks(norm.normalize(s))
        if len(o) != len(p):
            continue
        diff = [(a, b) for a, b in zip(o, p) if a != b]
        tot += sum(1 for a in o if a.isalpha())
        changed += len([1 for a, _ in diff if a.isalpha()])
        if diff and len(ex) < 6:
            ex.append((s, norm.normalize(s), diff[:3]))
    print(f"  {changed}/{tot} từ bị đổi = {100*changed/max(tot,1):.3f}%")
    for s, out, d in ex:
        print(f"   gốc: {s[:80]}")
        print(f"   sau: {out[:80]}  {d}")


if __name__ == "__main__":
    main()
