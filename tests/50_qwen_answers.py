"""Hỏi tự động 50 câu chuẩn cho một model, ghi kết quả ra JSONL.

Khác với việc dán vào giao diện chat: script gọi thẳng ``llm.chat`` nên KHÔNG
bị giới hạn 500 ký tự, KHÔNG bị bộ lọc chủ đề cắt, và không tốn lượt gõ tay.

Chỉ lo phần HỎI. Việc chấm điểm làm riêng bằng prompt judge.

Cách chạy::

    .venv/bin/python tests/50_qwen_answers.py --limit 2        # chạy thử
    .venv/bin/python tests/50_qwen_answers.py                  # chạy cả 50
    .venv/bin/python tests/50_qwen_answers.py --resume         # chạy tiếp nếu đứt
    .venv/bin/python tests/50_qwen_answers.py --provider gemini

Kết quả: ``data/sources/qwen_answers_50.jsonl``, mỗi dòng một câu::

    {"id": "q01", "question": "...", "answer": "...", "seconds": 34.2,
     "provider": "ollama", "model": "qwen3.5:4b", "error": ""}

Ghi ra file ngay sau MỖI câu, nên Ctrl-C giữa chừng không mất phần đã làm.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

QUESTIONS = ROOT / "data" / "sources" / "eval_questions_50.txt"
OUT_MODEL = ROOT / "data" / "sources" / "qwen_answers_50.jsonl"
OUT_PIPELINE = ROOT / "data" / "sources" / "pipeline_answers_50.jsonl"

# Prompt hệ thống: giữ đúng 6 quy tắc đã dùng khi soạn bộ eval.
# Cố ý KHÔNG yêu cầu xuất JSON ở đây — mỗi lần gọi chỉ một câu, trả lời tự do
# để judge đọc như câu trả lời thật của chatbot.
SYSTEM = """Bạn là trợ lý y khoa tiếng Việt. Trả lời câu hỏi của người dùng.

QUY TẮC BẮT BUỘC:
1. Trả lời bằng tiếng Việt, 4-6 gạch đầu dòng, ngắn gọn.
2. KHÔNG nêu liều thuốc cụ thể (không viết số mg, ml, số viên).
3. KHÔNG khẳng định chắc chắn một chẩn đoán; chỉ nêu khả năng và khuyên đi khám.
4. Câu nào thiếu thông tin (quá ngắn, mơ hồ) thì PHẢI hỏi lại triệu chứng, không được đoán bệnh.
5. Câu nào là cấp cứu thì phải nói rõ gọi 115 / đi bệnh viện ngay.
6. Cuối mỗi câu trả lời thêm: "Lưu ý: thông tin chỉ mang tính tham khảo, không thay thế bác sĩ."
"""

THINK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)


def load_questions(path: Path) -> list[tuple[str, str]]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        # định dạng: q01<TAB>câu hỏi   (chấp nhận cả khoảng trắng nếu thiếu tab)
        qid, _, question = line.partition("\t")
        if not question:
            qid, _, question = line.partition(" ")
        items.append((qid.strip(), question.strip()))
    if not items:
        raise SystemExit(f"Không đọc được câu hỏi nào từ {path}")
    return items


def load_done(path: Path) -> dict:
    done = {}
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # dòng hỏng do lần chạy trước bị cắt -> bỏ qua
        if rec.get("answer") and not rec.get("error"):
            done[rec["id"]] = rec
    return done


def clean(text: str) -> str:
    """Bỏ khối suy nghĩ của model reasoning, bỏ khoảng trắng thừa."""
    return THINK_RE.sub("", text).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(QUESTIONS))
    ap.add_argument("--out", default=None,
                    help="mặc định: qwen_answers_50.jsonl (model) / pipeline_answers_50.jsonl (pipeline)")
    ap.add_argument("--mode", choices=["model", "pipeline"], default="model",
                    help="model = chỉ gọi LLM (đo kiến thức model); "
                         "pipeline = qua normalizer + lọc chủ đề + truy xuất (đo cả hệ thống)")
    ap.add_argument("--provider", default=None, help="ollama | gemini (mặc định: theo .env)")
    ap.add_argument("--limit", type=int, default=0, help="chỉ chạy N câu đầu")
    ap.add_argument("--resume", action="store_true", help="bỏ qua câu đã có trả lời")
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--retry", type=int, default=1,
                    help="số lần thử lại khi câu trả lời rỗng/lỗi (mặc định 1)")
    ap.add_argument("--only", default="",
                    help="chỉ chạy các id này, cách nhau dấu phẩy (vd q16,q50)")
    ap.add_argument("--merge", action="store_true",
                    help="ghi đè từng câu vào file có sẵn, giữ nguyên các câu khác")
    args = ap.parse_args()

    from app.services import llm

    provider = args.provider or (llm.provider_chain() or ["ollama"])[0]
    model = llm.current_model()
    out_path = Path(args.out) if args.out else (OUT_PIPELINE if args.mode == "pipeline" else OUT_MODEL)

    bot = None
    if args.mode == "pipeline":
        from app.services.pipeline import MedicalChatbot
        print("Nạp pipeline (chromadb + embedder)...")
        bot = MedicalChatbot()
        bot.warmup()

    all_items = load_questions(Path(args.questions))
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    existing: list[dict] = []
    if args.merge and out_path.exists():
        existing = [json.loads(l) for l in out_path.open(encoding="utf-8") if l.strip()]
    elif not args.resume and out_path.exists():
        out_path.unlink()

    done = load_done(out_path) if args.resume else {}
    todo = [it for it in all_items if it[0] not in done]
    if only:
        todo = [it for it in todo if it[0] in only]
    if args.limit:
        todo = todo[: args.limit]

    def save(rec: dict) -> None:
        """Ghi ngay để Ctrl-C không mất phần đã chạy."""
        if args.merge:
            rows = existing if existing else []
            for r in rows:
                if r["id"] == rec["id"]:
                    r.clear(); r.update(rec); break
            else:
                rows.append(rec)
            with out_path.open("w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        else:
            with out_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Model: {provider} / {model}  | chế độ: {args.mode}")
    if done:
        print(f"Đã có sẵn: {len(done)} câu (bỏ qua)")
    print(f"Cần chạy: {len(todo)}/{len(all_items)} câu -> {out_path.name}\n")

    t_start = time.time()
    errors = 0
    for i, (qid, question) in enumerate(todo, 1):
        t0 = time.time()
        extra = {}
        attempt = 0
        while True:
            try:
                if bot is not None:
                    ans = bot.ask(question, provider=provider)
                    text = ans.text
                    extra = {"allowed": ans.allowed,
                             "sources": len(ans.sources or []),
                             "timings": ans.timings}
                else:
                    text = llm.chat(
                        [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": question}],
                        temperature=0.2, max_tokens=args.max_tokens, provider=provider,
                    )
                err = ""
            except Exception as exc:
                text, err = "", f"{type(exc).__name__}: {exc}"

            answer = clean(text)
            bad = (not answer
                   or "hệ thống đang gặp sự cố" in answer
                   or answer.startswith("Lưu ý: thông tin"))
            if bad and not err:
                err = ("câu trả lời rỗng hoặc chỉ có disclaimer "
                       "(kiểm tra ollama: ollama ps / log GPU)")
            if bad and attempt < args.retry:
                attempt += 1
                print(f"      ! {qid} lỗi, thử lại lần {attempt} sau 3s...")
                time.sleep(3)
                continue
            break
        dt = time.time() - t0

        if err:
            errors += 1

        rec = {"id": qid, "question": question, "answer": answer,
               "seconds": round(dt, 1), "provider": provider,
               "model": model, "mode": args.mode, "error": err}
        rec.update(extra)
        # ghi ngay để Ctrl-C không mất phần đã chạy
        save(rec)

        done_count = i
        avg = (time.time() - t_start) / done_count
        eta = (len(todo) - done_count) * avg / 60
        status = f"LỖI {err[:50]}" if err else f"{len(answer)} ký tự"
        print(f"  {i:>2}/{len(todo)} {qid}  {dt:5.1f}s  {status:<28} còn ~{eta:4.1f} phút")

    total = time.time() - t_start
    print(f"\nXong {len(todo)} câu trong {total / 60:.1f} phút -> {out_path}")
    if errors:
        print(f"CẢNH BÁO: {errors} câu lỗi. Chạy lại với --resume để làm lại phần thiếu.")
    print("\nBước tiếp: dán từng dòng trong file này vào prompt judge "
          "kèm khối tương ứng trong data/sources/eval_judge_inputs.md")


if __name__ == "__main__":
    main()
