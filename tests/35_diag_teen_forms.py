import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.normalizer import QueryNormalizer, TEEN, SINGLE


def main():
    n = QueryNormalizer()
    print("Từ teencode/đơn: số lần trong kb, trạng thái nhập nhằng, các dạng có dấu cùng khoá")
    for key in sorted(set(TEEN) | set(SINGLE)):
        if not key.isascii():
            continue
        alts = [(f, n.uni.get(f, 0)) for f in n.forms.get(key, []) if f != key]
        print(f"  {key:<6} self={n.uni.get(key, 0):<5} ambiguous={n._ambiguous(key)!s:<5} alts={alts}")

    print("\nMột số từ đời thường (dạng, số lần):")
    for key in ("meo", "cho", "ga", "heo", "chay", "chap", "lon", "trau", "vit", "bo"):
        print(f"  {key:<5}", [(f, n.uni.get(f, 0)) for f in n.forms.get(key, [])])


if __name__ == "__main__":
    main()