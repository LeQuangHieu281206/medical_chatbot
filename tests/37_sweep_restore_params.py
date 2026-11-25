import importlib.util
import json
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import app.services.normalizer as nm


def load_off():
    spec = importlib.util.spec_from_file_location("off34", ROOT / "tests/34_test_offtopic_noisy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.OFF


def accuracy(norm, sentences):
    tot = ok = sent_ok = used = 0
    for orig in sentences:
        noisy = nm.strip_diacritics(orig).lower()
        out = norm.normalize(noisy)
        o = nm.WORD_RE.findall(unicodedata.normalize("NFC", orig).lower())
        p = nm.WORD_RE.findall(out.lower())
        if len(o) != len(p):
            continue
        used += 1
        wrong = 0
        for a, b in zip(o, p):
            if not a.isalpha() or a in nm.TEEN or a in nm.SINGLE:
                continue
            tot += 1
            ok += a == b
            wrong += a != b
        sent_ok += wrong == 0
    return ok / max(tot, 1), sent_ok, used


def main():
    rows = [json.loads(l) for l in open(ROOT / "data/processed/eval_noisy.jsonl", encoding="utf-8") if l.strip()]
    med = [r["original"] for r in rows if r["mode"] == "nodiac"]
    off = load_off()

    tmp = Path(tempfile.mkdtemp()) / "lex.json"
    print(f"{'MIN_BIGRAM':<11}{'LAMBDA':<8}{'y tế (âm tiết)':<17}{'y tế (câu đúng)':<18}"
          f"{'ngoài CĐ (âm tiết)':<20}{'ngoài CĐ (câu đúng)'}")
    for mb in (1, 2):
        nm.MIN_BIGRAM = mb
        nm.build_lexicon(out_path=tmp)
        nm.LEX_PATH = tmp
        norm = nm.QueryNormalizer()
        for lam in (0.5, 0.65, 0.8, 0.9):
            nm.LAMBDA = lam
            a1, s1, n1 = accuracy(norm, med)
            a2, s2, n2 = accuracy(norm, off)
            mark = "  <- hiện tại" if (mb, lam) == (2, 0.8) else ""
            print(f"{mb:<11}{lam:<8}{100 * a1:>6.2f}%{'':<9}{s1:>4}/{n1:<12}"
                  f"{100 * a2:>6.2f}%{'':<11}{s2:>3}/{n2}{mark}")


if __name__ == "__main__":
    main()