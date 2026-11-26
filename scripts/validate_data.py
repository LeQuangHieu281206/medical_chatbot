"""Cổng kiểm tra chất lượng dữ liệu trước khi nạp vào ChromaDB.

Khác với `tests/40_data_audit.py` (chỉ đọc và ghi CSV, không bao giờ fail), script
này là **cổng chặn**: quy tắc mức `hard` sai thì exit code 1, để không ai nạp dữ
liệu lỗi vào vector DB. Quy tắc `soft` chỉ cảnh báo và ghi vào báo cáo.

Hợp đồng dữ liệu (ngưỡng + lý do) nằm ở `data/DATA_CONTRACT.md`.

Chạy:
    .venv/bin/python scripts/validate_data.py                    # kiểm tra mọi file đã biết
    .venv/bin/python scripts/validate_data.py data/processed/kb_drugs_25_full.jsonl
    .venv/bin/python scripts/validate_data.py --report data/audit/contract_report.md
    .venv/bin/python scripts/validate_data.py --strict           # coi cả soft là hard (dùng cho dữ liệu mới)
"""
import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.data_quality import find_duplicates, norm  # noqa: E402
from app.services.topic_taxonomy import (  # noqa: E402
    MIN_ROWS_PER_TOPIC,
    tag_topic,
)

PROCESSED = ROOT / "data/processed"

# --- ngưỡng của hợp đồng ------------------------------------------------
ANSWER_MIN = 100        # đáp án dưới 100 ký tự gần như không trả lời được gì
ANSWER_MAX = 2000       # trên 2000 ký tự thì bị cắt khi đưa vào prompt (MAX_QA_CHARS=350)
CHUNK_MIN = 80
CHUNK_MAX = 1200        # ~512 token của e5-small
LINK_MIN_PCT = 100.0    # dữ liệu mới: bắt buộc có nguồn
MIN_DRUGS = 200         # số hoạt chất tối thiểu để trả lời được câu hỏi về thuốc
DRUG_FACETS = {"indication", "contraindication", "caution", "adr", "interaction"}

# `link` không nằm trong trường bắt buộc: dữ liệu cũ thiếu nguồn là chuyện đã rồi,
# còn "100% có nguồn" là luật mềm để không chặn oan dữ liệu cũ.
QA_FIELDS = ("source", "question", "answer")

# kind: cách kiểm tra; link: có bắt buộc nguồn không; topics: có kiểm phủ chuyên khoa không
SPECS = {
    "kb.jsonl": dict(kind="qa", topics=True),
    "kb_drugs_25_full.jsonl": dict(kind="drug", topics=False),
    "kb_drugs_full.jsonl": dict(kind="drug", topics=False),
    "eval.jsonl": dict(kind="qa", topics=False),
    "kb_chunked.jsonl": dict(kind="chunk"),
    "eval_noisy.jsonl": dict(kind="noisy"),
    "ner_train.jsonl": dict(kind="ner"),
    "ner_dev.jsonl": dict(kind="ner"),
    "ner_test.jsonl": dict(kind="ner"),
    "red_flags.jsonl": dict(kind="redflag"),
}
DEFAULT_FILES = [
    "kb.jsonl", "kb_drugs_25_full.jsonl", "kb_drugs_full.jsonl", "eval.jsonl",
    "kb_merged.jsonl", "kb_chunked.jsonl", "kb_merged_chunked.jsonl", "eval_noisy.jsonl",
    "ner_train.jsonl", "ner_dev.jsonl", "ner_test.jsonl",
    "sources/red_flags.jsonl",
]


def spec_for(name: str) -> dict:
    """Chọn cách kiểm tra theo tên file; tên lạ mặc định là KB hỏi đáp."""
    if name in SPECS:
        return SPECS[name]
    if "red_flags" in name:      # kể cả bản ứng viên red_flags_candidate.jsonl
        return dict(kind="redflag")
    if name.endswith("_chunked.jsonl"):
        return dict(kind="chunk")
    if name.startswith("kb_drugs"):
        return dict(kind="drug", topics=False)
    if name.startswith("kb"):
        return dict(kind="qa", topics=True)
    return dict(kind="qa", topics=False)


@dataclass
class Result:
    rule: str
    level: str      # "hard" | "soft"
    ok: bool
    detail: str


@dataclass
class Report:
    path: Path
    total: int
    results: list


def load_jsonl(path: Path) -> tuple[list, list]:
    """Trả về (rows, lỗi parse). Dòng hỏng không làm chết cả file."""
    rows, bad = [], []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            bad.append(f"dòng {i}: {e.msg}")
    return rows, bad


def _blank(v) -> bool:
    """Rỗng thật sự: None, chuỗi trắng, hoặc list/dict rỗng. Số 0 vẫn là giá trị hợp lệ."""
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, dict)):
        return not v
    return False


def check_fields(rows, fields) -> Result:
    missing = Counter()
    for r in rows:
        for f in fields:
            if _blank(r.get(f)):
                missing[f] += 1
    if not missing:
        return Result(f"trường bắt buộc {', '.join(fields)}", "hard", True, "đủ")
    detail = ", ".join(f"{f}: {n} dòng" for f, n in missing.items())
    return Result(f"trường bắt buộc {', '.join(fields)}", "hard", False, detail)


def check_answer_len(rows) -> Result:
    short = [r for r in rows if len(r.get("answer") or "") < ANSWER_MIN]
    long_ = [r for r in rows if len(r.get("answer") or "") > ANSWER_MAX]
    detail = f"< {ANSWER_MIN} ký tự: {len(short)}, > {ANSWER_MAX}: {len(long_)}"
    return Result(f"độ dài đáp án {ANSWER_MIN}–{ANSWER_MAX}", "soft",
                  not short and not long_, detail)


def check_link(rows) -> Result:
    have = sum(1 for r in rows if not _blank(r.get("link")))
    pct = 100 * have / len(rows) if rows else 0
    return Result("100% dòng có link nguồn", "soft", pct >= LINK_MIN_PCT,
                  f"{have}/{len(rows)} ({pct:.1f}%)")


def check_dup(rows) -> tuple[Result, Result]:
    keys = Counter(norm(r.get("question") or "") for r in rows)
    keys.pop("", None)
    exact = sum(v - 1 for v in keys.values() if v > 1)
    r1 = Result("không có câu hỏi trùng khít", "hard", exact == 0,
                f"{exact} dòng dư ({sum(1 for v in keys.values() if v > 1)} nhóm)")
    groups, _ = find_duplicates(rows)
    extra = sum(len(v) - 1 for v in groups.values())
    r2 = Result("không có câu hỏi gần trùng (Jaccard ≥ 0.70)", "soft", extra == 0,
                f"{extra} dòng dư ({len(groups)} nhóm) — xem data/audit/duplicates.csv")
    return r1, r2


def _drug_slug(row) -> str:
    return (row.get("link") or "").rstrip("/").split("/")[-1].lower()


def check_topics(rows) -> Result:
    dist = Counter(tag_topic(r.get("question") or "", r.get("answer") or "") for r in rows)
    thin = sorted((n, t) for t, n in dist.items() if n < MIN_ROWS_PER_TOPIC)
    detail = "; ".join(f"{t} {n}" for n, t in thin) or "mọi chủ đề đủ ngưỡng"
    return Result(f"mỗi chủ đề ≥ {MIN_ROWS_PER_TOPIC} câu", "soft", not thin,
                  f"{len(thin)} chủ đề mỏng: {detail}" if thin else detail)


def check_drugs(rows) -> list:
    per_drug = {}
    pairs = Counter()
    for r in rows:
        per_drug.setdefault(_drug_slug(r), set()).add(r.get("facet"))
        pairs[(_drug_slug(r), r.get("facet"))] += 1
    enough = len(per_drug) >= MIN_DRUGS
    r1 = Result(f"≥ {MIN_DRUGS} hoạt chất", "soft", enough, f"có {len(per_drug)}")
    incomplete = {d: DRUG_FACETS - f for d, f in per_drug.items() if DRUG_FACETS - f}
    r2 = Result("mỗi hoạt chất đủ 5 khía cạnh", "soft", not incomplete,
                f"{len(incomplete)} hoạt chất thiếu: " +
                ", ".join(f"{d}({','.join(sorted(v))})" for d, v in list(incomplete.items())[:5])
                if incomplete else "đủ")
    dup = {k: v for k, v in pairs.items() if v > 1}
    r3 = Result("mỗi (hoạt chất, khía cạnh) chỉ 1 dòng", "hard", not dup,
                f"{len(dup)} cặp lặp" if dup else "đủ")
    bad_facet = {r.get("facet") for r in rows} - DRUG_FACETS
    r4 = Result("facet thuộc 5 khía cạnh đã định", "hard", not bad_facet,
                "facet lạ: " + ", ".join(sorted(map(str, bad_facet))) if bad_facet else "đủ")
    return [r1, r2, r3, r4]


def check_chunk(rows, path: Path) -> list:
    out = [check_fields(rows, ("parent_id", "question", "text"))]
    short = sum(1 for r in rows if len(r.get("text") or "") < CHUNK_MIN)
    long_ = sum(1 for r in rows if len(r.get("text") or "") > CHUNK_MAX)
    out.append(Result(f"độ dài chunk {CHUNK_MIN}–{CHUNK_MAX}", "soft",
                      not short and not long_, f"quá ngắn: {short}, quá dài: {long_}"))

    # kb_merged_chunked.jsonl ↔ kb_merged.jsonl; kb_chunked.jsonl ↔ kb.jsonl
    kb_path = PROCESSED / path.name.replace("_chunked.jsonl", ".jsonl")
    if kb_path.exists():
        n_kb, _ = load_jsonl(kb_path)
        bad = sum(1 for r in rows if not isinstance(r.get("parent_id"), int)
                  or not 0 <= r["parent_id"] < len(n_kb))
        out.append(Result("parent_id trỏ đúng dòng KB cha", "hard", bad == 0,
                          f"{bad} chunk trỏ sai ({kb_path.name} có {len(n_kb)} dòng)"))
        # parent_id đúng khoảng nhưng lệch dòng là lỗi im lặng nguy hiểm nhất:
        # chunk của câu A bị ghép vào câu B khi expand.
        shifted = sum(1 for r in rows
                      if isinstance(r.get("parent_id"), int)
                      and 0 <= r["parent_id"] < len(n_kb)
                      and norm(r.get("question") or "") != norm(n_kb[r["parent_id"]].get("question") or ""))
        out.append(Result("câu hỏi chunk khớp câu hỏi cha", "hard", shifted == 0,
                          f"{shifted} chunk lệch cha — cần chạy lại scripts/rechunk_qa.py"
                          if shifted else "đủ"))
    return out


def check_ner(rows) -> list:
    labels_path = PROCESSED / "ner_labels.json"
    allowed = set(json.loads(labels_path.read_text(encoding="utf-8"))) if labels_path.exists() else None
    mismatched = sum(1 for r in rows if len(r.get("tokens") or []) != len(r.get("labels") or []))
    out = [Result("tokens và labels cùng độ dài", "hard", mismatched == 0,
                  f"{mismatched} dòng lệch")]
    if allowed:
        unknown = {l for r in rows for l in (r.get("labels") or []) if l not in allowed}
        out.append(Result("nhãn nằm trong ner_labels.json", "hard", not unknown,
                          "nhãn lạ: " + ", ".join(sorted(unknown)) if unknown else "đủ"))
    return out


def check_noisy(rows) -> list:
    return [check_fields(rows, ("id", "mode", "original", "noisy"))]


# Liều thuốc trong lời khuyên sơ cứu là nguy hiểm: người dùng có thể làm theo
DOSE_IN_ADVICE = re.compile(r"\d+\s*(mg|mcg|µg|μg|ml|gói|ống|viên)\b", re.IGNORECASE)
RED_FLAG_FIELDS = ("id", "nhom", "uu_tien", "mau", "loi_khuyen")
RED_FLAG_OPTIONAL = ("khong_khop", "khong_khop_tru", "kem_theo", "khong_duoc_lam", "nguon")
# trường truy vết nguồn: bắt buộc có để biết mỗi nhóm dựa vào văn bản/hướng dẫn nào
RED_FLAG_TRACE = ("nguon", "nguon_loai", "phien_ban", "ngay_kiem_duyet")
NGUON_LOAI = {"văn bản BYT", "hướng dẫn bệnh viện", "quốc tế"}
RED_FLAG_MIN_GROUPS = 12
RED_FLAG_MIN_SAMPLES = 3


def check_red_flags(rows) -> list:
    """Nhóm dấu hiệu cấp cứu: đủ trường, đủ mẫu, lời khuyên an toàn."""
    out = [check_fields(rows, RED_FLAG_FIELDS)]
    ids = [r.get("id") for r in rows]
    dup = {i for i in ids if ids.count(i) > 1}
    out.append(Result("id mỗi nhóm là duy nhất", "hard", not dup,
                      ", ".join(sorted(dup)) if dup else "đủ"))
    pri = [r.get("uu_tien") for r in rows]
    dup_pri = {p for p in pri if pri.count(p) > 1}
    out.append(Result("uu_tien là số duy nhất", "hard", not dup_pri,
                      ", ".join(map(str, sorted(dup_pri))) if dup_pri else "đủ"))
    bad_opt = [r.get("id") for r in rows for k in ("khong_khop", "khong_khop_tru", "kem_theo", "khong_duoc_lam")
               if k in r and (not isinstance(r[k], list) or not all(isinstance(x, str) and x.strip()
                                                                   for x in r[k]))]
    out.append(Result("khong_khop/kem_theo/khong_duoc_lam là danh sách chuỗi", "hard",
                      not bad_opt, ", ".join(map(str, bad_opt)) if bad_opt else "sạch"))
    bad_src = [r.get("id") for r in rows
               if not isinstance(r.get("nguon"), str) or not r.get("nguon", "").strip()]
    out.append(Result("mỗi nhóm ghi nguồn chuyên môn", "hard", not bad_src,
                      ", ".join(map(str, bad_src)) if bad_src else "đủ"))
    bad_kind = [r.get("id") for r in rows if r.get("nguon_loai") not in NGUON_LOAI]
    out.append(Result("nguon_loai thuộc BYT / bệnh viện / quốc tế", "hard", not bad_kind,
                      ", ".join(map(str, bad_kind)) if bad_kind else "đủ"))
    few = [r.get("id") for r in rows if len(r.get("mau") or []) < RED_FLAG_MIN_SAMPLES]
    out.append(Result(f"mỗi nhóm ≥ {RED_FLAG_MIN_SAMPLES} mẫu câu", "hard", not few,
                      ", ".join(map(str, few)) if few else "đủ"))
    out.append(Result(f"≥ {RED_FLAG_MIN_GROUPS} nhóm cấp cứu", "hard",
                      len(rows) >= RED_FLAG_MIN_GROUPS, f"có {len(rows)}"))
    bad_advice = [r.get("id") for r in rows if not (r.get("loi_khuyen") or [])]
    out.append(Result("mỗi nhóm có lời khuyên sơ cứu", "hard", not bad_advice,
                      ", ".join(map(str, bad_advice)) if bad_advice else "đủ"))
    dose = [r.get("id") for r in rows
            if any(DOSE_IN_ADVICE.search(l) for l in (r.get("loi_khuyen") or []))]
    out.append(Result("lời khuyên không chứa liều thuốc", "hard", not dose,
                      ", ".join(map(str, dose)) if dose else "sạch"))
    # Mẫu câu phải so khớp được câu đã chuẩn hoá: không dùng ký tự regex đặc biệt
    meta = [m for r in rows for m in (r.get("mau") or []) + (r.get("khong_khop") or []) + (r.get("khong_khop_tru") or []) + (r.get("kem_theo") or [])
            if re.search(r"[()\[\]{}*+?^$\\|]", m.replace("...", ""))]
    out.append(Result("mẫu câu là chuỗi thường (chỉ cho phép ...)", "hard", not meta,
                      ", ".join(meta[:3]) if meta else "sạch"))
    return out


def validate(path: Path, spec: dict) -> Report:
    rows, bad = load_jsonl(path)
    results = [Result("parse JSONL", "hard", not bad,
                      bad[0] if bad else f"{len(rows)} dòng hợp lệ")]
    kind = spec.get("kind", "qa")

    if kind in ("qa", "drug"):
        results.append(check_fields(rows, QA_FIELDS))
        results.append(check_answer_len(rows))
        results.append(check_link(rows))
        if kind == "drug":
            # Câu hỏi theo mẫu "X được chỉ định trong..." nên gần trùng là giả;
            # kiểm trùng theo (hoạt chất, khía cạnh) mới đúng.
            results.append(check_dup(rows)[0])
            results += check_drugs(rows)
        else:
            results += check_dup(rows)
        if spec.get("topics"):
            results.append(check_topics(rows))
    elif kind == "chunk":
        results += check_chunk(rows, path)
    elif kind == "ner":
        results += check_ner(rows)
    elif kind == "noisy":
        results += check_noisy(rows)
    elif kind == "redflag":
        results += check_red_flags(rows)

    return Report(path, len(rows), results)


def print_report(rep: Report, strict: bool):
    rel = rep.path.relative_to(ROOT) if rep.path.is_relative_to(ROOT) else rep.path
    print(f"\n== {rel}  ({rep.total} dòng) ==")
    for r in rep.results:
        failed = not r.ok
        hard = r.level == "hard" or strict
        tag = "FAIL" if failed and hard else "WARN" if failed else "PASS"
        print(f"  [{tag}] {r.rule:<48} {r.detail}")


def failed_hard(reports, strict: bool) -> int:
    n = 0
    for rep in reports:
        for r in rep.results:
            if not r.ok and (r.level == "hard" or strict):
                n += 1
    return n


def write_markdown(reports, strict: bool, out: Path):
    lines = ["# Báo cáo hợp đồng dữ liệu",
             "",
             f"Sinh bởi `scripts/validate_data.py` ({'strict' if strict else 'lenient'}).",
             f"Ngưỡng: xem `data/DATA_CONTRACT.md`.",
             ""]
    for rep in reports:
        rel = rep.path.relative_to(ROOT) if rep.path.is_relative_to(ROOT) else rep.path
        lines += [f"## `{rel}` — {rep.total} dòng", "",
                  "| trạng thái | luật | mức | chi tiết |", "|---|---|---|---|"]
        for r in rep.results:
            failed = not r.ok
            hard = r.level == "hard" or strict
            state = "FAIL" if failed and hard else "WARN" if failed else "PASS"
            lines.append(f"| {state} | {r.rule} | {r.level} | {r.detail} |")
        lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nĐã ghi báo cáo: {out.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description="Cổng kiểm tra chất lượng dữ liệu")
    ap.add_argument("files", nargs="*", help="file .jsonl cần kiểm tra (mặc định: các file đã biết)")
    ap.add_argument("--report", help="ghi báo cáo Markdown, ví dụ data/audit/contract_report.md")
    ap.add_argument("--strict", action="store_true",
                    help="coi cả luật soft là hard (dùng khi duyệt dữ liệu mới)")
    args = ap.parse_args()

    targets = [Path(f) for f in args.files] or [
        (ROOT / "data" / f) if f.startswith("sources/") else (PROCESSED / f)
        for f in DEFAULT_FILES
    ]
    reports = []
    for path in targets:
        if not path.exists():
            print(f"\n== {path} ==\n  [FAIL] file không tồn tại")
            reports.append(Report(path, 0, [Result("tồn tại", "hard", False, "không thấy file")]))
            continue
        reports.append(validate(path, spec_for(path.name)))
        print_report(reports[-1], args.strict)

    if args.report:
        write_markdown(reports, args.strict, ROOT / args.report)

    n = failed_hard(reports, args.strict)
    print(f"\n{'ĐẠT' if n == 0 else 'KHÔNG ĐẠT'}: {n} luật hard sai. "
          f"Không nạp ChromaDB khi còn luật hard sai.")
    return 0 if n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
