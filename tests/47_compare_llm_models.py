"""So sánh các model LLM trên cùng một câu hỏi: độ trễ, token, câu trả lời.

Vì sao có script này: chất lượng model trên tiếng Việt y khoa không đoán được
bằng tên model. Chạy trên vài câu thật của bạn rồi tự so.

Cách chạy:
    # chỉ so các model cloud
    .venv/bin/python tests/47_compare_llm_models.py \
        --q "tôi bị đau dạ dày sau khi ăn, nên làm gì?" \
        gemini:gemini-3.5-flash gemini:gemini-3.8-flash

    # thêm mốc so sánh là model local
    .venv/bin/python tests/47_compare_llm_models.py --q "..." \
        local:qwen3.5:4b gemini:gemini-3.5-flash

Tiền tố `local:` = Ollama, `gemini:` = Gemini. Model Gemini cần GEMINI_API_KEY
(trong biến môi trường hoặc file .env ở thư mục gốc).

Lưu ý chi phí: mỗi model × mỗi câu là một lần gọi thật. Bắt đầu với 1-2 câu.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import llm  # noqa: E402

SYSTEM = (
    "Bạn là trợ lý y tế tiếng Việt. Trả lời ngắn gọn, rõ ràng, bằng tiếng Việt, "
    "dựa trên kiến thức y khoa thông thường. Luôn nhắc người bệnh đi khám bác sĩ "
    "khi cần."
)


def run_one(spec: str, question: str, max_tokens: int) -> dict:
    """Gọi một model và gom lại kết quả để in thành bảng."""
    provider, _, name = spec.partition(":")
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    result = {"spec": spec, "text": "", "stats": {}, "error": ""}
    try:
        if provider == "local":
            gen = llm._ollama_stream(messages, 0.2, max_tokens, llm.DEFAULT_NUM_CTX, name)
        elif provider == "gemini":
            if not llm.gemini_ready():
                raise RuntimeError("thiếu GEMINI_API_KEY (dùng .env)")
            gen = llm._gemini_stream(messages, 0.2, max_tokens, None, name)
        else:
            raise ValueError(f"tiền tố không hiểu: {spec!r} (dùng local: hoặc gemini:)")
        for kind, val in gen:
            if kind == "token":
                result["text"] += val
            else:
                result["stats"] = val
    except Exception as exc:                      # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="So sánh model LLM trên cùng câu hỏi")
    ap.add_argument("--q", action="append", default=[],
                    help="câu hỏi (lặp lại nhiều lần để thử nhiều câu)")
    ap.add_argument("--max-tokens", type=int, default=250)
    ap.add_argument("models", nargs="+", help="vd: local:qwen3.5:4b gemini:gemini-3.5-flash")
    args = ap.parse_args()

    questions = args.q or ["tôi bị đau dạ dày sau khi ăn, nên làm gì?"]

    for qi, question in enumerate(questions, 1):
        print("=" * 78)
        print(f"CÂU {qi}: {question}")
        print("=" * 78)
        rows = []
        for spec in args.models:
            r = run_one(spec, question, args.max_tokens)
            rows.append(r)
            st = r["stats"] or {}
            if r["error"]:
                print(f"\n[{spec}] LỖI: {r['error']}")
                continue
            print(f"\n[{spec}]")
            print(f"  ttft={st.get('ttft_s')}s  tổng={st.get('total_s')}s  "
                  f"prompt={st.get('prompt_tokens')}  sinh={st.get('gen_tokens')} token")
            print("  " + r["text"].strip().replace("\n", "\n  ")[:900])
        print()

        ok = [r for r in rows if not r["error"]]
        if len(ok) > 1:
            ok.sort(key=lambda r: (r["stats"] or {}).get("total_s") or 1e9)
            print("Xếp theo thời gian trả lời (nhanh nhất trước):")
            for r in ok:
                st = r["stats"]
                print(f"  {r['spec']:<34} {st.get('total_s')}s  "
                      f"{st.get('gen_tokens')} token")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
