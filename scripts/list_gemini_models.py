"""Liệt kê các model mà API key Gemini của bạn dùng được.

Một API key Gemini KHÔNG gắn với một model cụ thể: key mở quyền cho tài khoản/
project, còn model được chọn ở tham số `model=` mỗi lần gọi. Script này cho biết
key của bạn thấy những model nào, để bạn điền đúng tên vào GEMINI_MODEL.

Cách chạy:
    .venv/bin/python scripts/list_gemini_models.py

Key được đọc từ biến môi trường GEMINI_API_KEY (hoặc GOOGLE_API_KEY), hoặc từ
file `.env` ở thư mục gốc dự án.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import llm  # noqa: E402


def _supports_generate(model) -> bool:
    """Model có sinh văn bản được không (tên thuộc tính đổi giữa các version SDK)."""
    for attr in ("supported_actions", "supported_generation_methods"):
        actions = getattr(model, attr, None)
        if actions:
            return any("generateContent" in str(a) for a in actions)
    return True          # không rõ thì cứ hiện ra


def main() -> int:
    if not llm.gemini_ready():
        print("Chưa có API key.\n")
        print("  1. Lấy key ở https://aistudio.google.com/apikey")
        print("  2. Tạo file .env ở thư mục gốc dự án (copy từ .env.example)")
        print("  3. Điền dòng: GEMINI_API_KEY=...")
        print("  4. Chạy lại script này")
        return 1

    client = llm._gemini_client_get()
    try:
        models = list(client.models.list())
    except Exception as exc:                      # noqa: BLE001
        print(f"Không lấy được danh sách model: {type(exc).__name__}: {exc}")
        print("\nThường là do key sai hoặc chưa bật Gemini API cho project.")
        return 1

    rows = []
    for m in models:
        name = (getattr(m, "name", "") or "").replace("models/", "")
        if not name or not _supports_generate(m):
            continue
        rows.append((name, getattr(m, "display_name", "") or "",
                     getattr(m, "input_token_limit", "") or ""))
    rows.sort()

    if not rows:
        print("Key hợp lệ nhưng không thấy model nào sinh văn bản được.")
        return 1

    print(f"Key này dùng được {len(rows)} model sinh văn bản:\n")
    width = max(len(r[0]) for r in rows)
    for name, display, limit in rows:
        note = f"  [{display}]" if display and display != name else ""
        tok = f"  ctx={limit}" if limit else ""
        print(f"  {name:<{width}}{note}{tok}")

    print("\nChọn một tên ở trên rồi điền vào .env, ví dụ:")
    print(f"  GEMINI_MODEL={rows[0][0]}")
    print("\nNếu phân vân: chọn bản 'flash' cho nhanh/rẻ, 'pro' khi cần suy luận sâu.")
    print("Đổi xong kiểm tra bằng: .venv/bin/python -c \"import sys; sys.path.insert(0,'.'); "
          "from app.services import llm; print(llm.PROVIDER, llm.GEMINI_MODEL)\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
