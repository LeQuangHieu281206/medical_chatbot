"""Lớp gọi LLM dùng chung: Ollama (chạy trên máy) hoặc Gemini (qua API key).

Nguyên tắc của dự án là **local-first**: Ollama là mặc định, Gemini chỉ bật khi
có cấu hình. Nhờ vậy:

  * Không có mạng vẫn chạy được.
  * Câu hỏi ngoài chủ đề bị bộ lọc local từ chối thì KHÔNG bao giờ rời khỏi máy.
  * Số đo trên bộ eval ổn định, vì model local đứng yên (Gemini có thể bị đổi
    ngầm bởi Google).

Cấu hình bằng biến môi trường:

  LLM_PROVIDER   ollama (mặc định) | gemini | auto
                 auto = thử Ollama trước, lỗi thì chuyển Gemini (nếu có key)
  OLLAMA_MODEL   mặc định "qwen3.5:4b"
  GEMINI_MODEL   mặc định "gemini-2.5-flash" (tên model đổi khá nhanh, nên
                 kiểm tra lại ở https://ai.google.dev/gemini-api/docs/models)
  GEMINI_API_KEY (hoặc GOOGLE_API_KEY) — bắt buộc khi dùng Gemini

Hai hàm công khai trả về cùng một dạng cho cả hai provider, nên phần còn lại
của pipeline không cần biết đang chạy model nào:

  chat(messages, ...)        -> str
  chat_stream(messages, ...) -> ("token", str) ... rồi ("stats", dict)
"""

from __future__ import annotations

import itertools
import os
import re
import time
from pathlib import Path
from typing import Iterator

import ollama

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    """Đọc .env ở thư mục gốc dự án; biến đã có trong môi trường thì giữ nguyên.

    Cố ý không cần thư viện ngoài: chỉ cần KEY=VALUE, bỏ qua dòng trống và
    dòng bắt đầu bằng #.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

# Đọc SAU khi nạp .env, nếu không các biến trong .env sẽ bị bỏ qua


def _env(name: str, default: str) -> str:
    """Như os.getenv nhưng coi giá trị rỗng là "chưa đặt".

    Cần thiết vì .env mẫu có dòng `GEMINI_MODEL=` để trống; nếu đọc thẳng thì
    model thành chuỗi rỗng và mọi lệnh gọi đều lỗi.
    """
    val = (os.getenv(name) or "").strip()
    return val or default


PROVIDER = _env("LLM_PROVIDER", "ollama").strip().lower()
OLLAMA_MODEL = _env("OLLAMA_MODEL", "qwen3.5:4b")
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
# Model rẻ/nhanh cho việc phân loại YES/NO (chỉ cần 8 token), tách khỏi model sinh
# câu trả lời để bộ lọc không kéo độ trễ và chi phí của model lớn.
GEMINI_MODEL_FAST = _env("GEMINI_MODEL_FAST", "gemini-3.5-flash-lite")
# off = tắt phần suy luận (mặc định: cần cho RAG vì max_output_tokens chỉ 400,
#       bật suy luận thì nó ăn hết ngân sách và câu trả lời bị cụt/rỗng)
# low = để suy luận mức thấp | auto = không can thiệp, dùng mặc định của model
GEMINI_THINKING = _env("GEMINI_THINKING", "off").lower()
DEFAULT_NUM_CTX = int(_env("NUM_CTX", "4096"))
KEEP_ALIVE = _env("KEEP_ALIVE", "30m")

# Lần gọi Gemini lỗi gần nhất, để API báo cho người dùng biết vì sao chậm/khác
LAST_ERROR = {"provider": "", "error": ""}

_gemini_client = None


def gemini_ready() -> bool:
    return bool(GEMINI_KEY)


def current_model() -> str:
    """Tên model đang phục vụ, để ghi vào log/số đo."""
    if PROVIDER == "gemini":
        return GEMINI_MODEL
    return OLLAMA_MODEL


def provider_chain() -> list:
    """Thứ tự provider sẽ thử, theo cấu hình."""
    if PROVIDER == "gemini":
        return ["gemini"]
    if PROVIDER == "auto":
        return ["ollama", "gemini"] if GEMINI_KEY else ["ollama"]
    return ["ollama"]


def available_providers() -> list:
    """Danh sách cho giao diện dựng menu chọn model."""
    return [
        {
            "id": "ollama",
            "label": f"Qwen · {OLLAMA_MODEL}",
            "model": OLLAMA_MODEL,
            "ready": True,
            "note": "Chạy trên máy, câu hỏi không rời khỏi máy.",
        },
        {
            "id": "gemini",
            "label": f"Gemini · {GEMINI_MODEL}",
            "model": GEMINI_MODEL,
            "ready": gemini_ready(),
            "note": "Cần mạng; nội dung câu hỏi được gửi tới Google.",
        },
    ]


def chain_for(provider: str | None) -> list:
    """Thứ tự provider thử cho một lựa chọn cụ thể từ giao diện.

    Chọn thẳng một provider thì dùng đúng nó, không âm thầm chuyển sang model
    khác — người dùng đang muốn so sánh, đổi ngầm sẽ làm kết quả vô nghĩa.
    """
    if provider in ("ollama", "gemini"):
        return [provider]
    return provider_chain()


# ---------------------------------------------------------------- Ollama

def _ollama_chat(messages, temperature, max_tokens, num_ctx, model=None) -> str:
    resp = ollama.chat(
        model=model or OLLAMA_MODEL,
        messages=messages,
        think=False,
        keep_alive=KEEP_ALIVE,
        options={
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
        },
    )
    return resp["message"]["content"]


def _ollama_stream(messages, temperature, max_tokens, num_ctx, model=None):
    t0 = time.perf_counter()
    ttft = None
    stream = ollama.chat(
        model=model or OLLAMA_MODEL,
        messages=messages,
        think=False,
        stream=True,
        keep_alive=KEEP_ALIVE,
        options={
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
        },
    )
    stats = {}
    for chunk in stream:
        piece = chunk["message"]["content"]
        if piece:
            if ttft is None:
                ttft = time.perf_counter() - t0
            yield "token", piece
        if getattr(chunk, "done", False):
            stats = {
                "prompt_tokens": getattr(chunk, "prompt_eval_count", None),
                "gen_tokens": getattr(chunk, "eval_count", None),
                "prompt_s": round((getattr(chunk, "prompt_eval_duration", 0) or 0) / 1e9, 1),
                "gen_s": round((getattr(chunk, "eval_duration", 0) or 0) / 1e9, 1),
            }
    stats.update(model=model or OLLAMA_MODEL, provider="ollama",
                 ttft_s=round(ttft, 2) if ttft is not None else None,
                 total_s=round(time.perf_counter() - t0, 1))
    yield "stats", stats


# ---------------------------------------------------------------- Gemini

def _gemini_client_get():
    global _gemini_client
    if not GEMINI_KEY:
        raise RuntimeError(
            "Chưa có GEMINI_API_KEY. Đặt biến môi trường rồi chạy lại, "
            "hoặc dùng LLM_PROVIDER=ollama.")
    if _gemini_client is None:
        try:
            from google import genai      # import muộn: không bắt buộc cài
        except ImportError as exc:
            raise RuntimeError(
                "Chưa cài SDK Gemini. Chạy: .venv/bin/pip install google-genai"
            ) from exc
        _gemini_client = genai.Client(api_key=GEMINI_KEY)
    return _gemini_client


# Gemini 2.5 dùng thinking_budget, Gemini 3.x/4 dùng thinking_level: hai API khác
# nhau và model sẽ báo lỗi nếu gửi sai. Đoán theo tên model, đoán sai thì tự đổi
# và thử lại một lần (xem _THINK_FALLBACK).
_THINK_STYLE: dict = {}


def _think_style(model: str) -> str:
    if model not in _THINK_STYLE:
        _THINK_STYLE[model] = "budget" if re.match(r"gemini-2\.", model) else "level"
    return _THINK_STYLE[model]


def _thinking_cfg(types, model: str):
    if GEMINI_THINKING == "auto":
        return None
    if _think_style(model) == "budget":
        return types.ThinkingConfig(thinking_budget=0 if GEMINI_THINKING == "off" else 512)
    return types.ThinkingConfig(
        thinking_level="MINIMAL" if GEMINI_THINKING == "off" else "LOW")


def _is_thinking_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "thinking" in text and ("invalid" in text or "unsupported" in text
                                   or "not supported" in text)


def _flip_think_style(model: str) -> None:
    _THINK_STYLE[model] = "level" if _think_style(model) == "budget" else "budget"


def _gemini_payload(messages, temperature, max_tokens, model=None):
    """Đổi messages kiểu OpenAI sang (system_instruction, contents, config)."""
    from google.genai import types

    system = " ".join(m["content"] for m in messages if m["role"] == "system").strip()
    turns = [m for m in messages if m["role"] != "system"]
    if len(turns) == 1 and turns[0]["role"] == "user":
        contents = turns[0]["content"]
    else:
        contents = [
            types.Content(
                role="model" if t["role"] == "assistant" else "user",
                parts=[types.Part(text=t["content"])],
            )
            for t in turns
        ]
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system or None,
        thinking_config=_thinking_cfg(types, model) if model else None,
    )
    return contents, cfg


def _gemini_chat(messages, temperature, max_tokens, num_ctx=None, model=None) -> str:
    client = _gemini_client_get()
    name = model or GEMINI_MODEL
    for attempt in (0, 1):
        contents, cfg = _gemini_payload(messages, temperature, max_tokens, name)
        try:
            resp = client.models.generate_content(
                model=name, contents=contents, config=cfg)
        except Exception as exc:                  # noqa: BLE001
            if attempt == 0 and _is_thinking_error(exc):
                _flip_think_style(name)
                continue
            raise
        text = (getattr(resp, "text", None) or "").strip()
        if not text:
            # Không có chữ nào: thường do suy luận ăn hết max_output_tokens
            raise RuntimeError(
                f"{name} trả về rỗng (có thể do thinking chiếm hết max_output_tokens="
                f"{max_tokens}). Thử GEMINI_THINKING=off hoặc tăng max_tokens.")
        return text


def _gemini_stream(messages, temperature, max_tokens, num_ctx=None, model=None):
    client = _gemini_client_get()
    name = model or GEMINI_MODEL
    t0 = time.perf_counter()
    ttft = None
    usage = None
    stream = None
    for attempt in (0, 1):
        contents, cfg = _gemini_payload(messages, temperature, max_tokens, name)
        try:
            # Lấy chunk đầu để lỗi tham số lộ ra ngay, rồi nối phần CÒN LẠI
            # của cùng iterator (không được tạo iterator mới, sẽ mất các chunk sau).
            it = iter(client.models.generate_content_stream(
                model=name, contents=contents, config=cfg))
            first = next(it, None)
            stream = itertools.chain([first], it) if first is not None else it
            break
        except Exception as exc:                  # noqa: BLE001
            if attempt == 0 and _is_thinking_error(exc):
                _flip_think_style(name)
                continue
            raise
    for chunk in stream:
        text = getattr(chunk, "text", None)
        if text:
            if ttft is None:
                ttft = time.perf_counter() - t0
            yield "token", text
        # usage_metadata chỉ đầy đủ ở chunk cuối
        if getattr(chunk, "usage_metadata", None):
            usage = chunk.usage_metadata
    yield "stats", {
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "gen_tokens": getattr(usage, "candidates_token_count", None),
        "prompt_s": None,       # Gemini không trả thời gian, chỉ có tổng
        "gen_s": round(time.perf_counter() - t0, 1),
        "model": model or GEMINI_MODEL,
        "provider": "gemini",
        "ttft_s": round(ttft, 2) if ttft is not None else None,
        "total_s": round(time.perf_counter() - t0, 1),
    }


# ---------------------------------------------------------------- Công khai

def chat(messages, temperature: float = 0.2, max_tokens: int = 400,
         num_ctx: int = DEFAULT_NUM_CTX, model: str | None = None,
         fast: bool = False, provider: str | None = None) -> str:
    """Gọi LLM không streaming, trả về chuỗi trả lời.

    `fast=True` dùng model rẻ (GEMINI_MODEL_FAST) cho tác vụ đơn giản như phân
    loại chủ đề; Ollama bỏ qua cờ này vì model local đã sẵn trong VRAM.
    """
    last = None
    for prov in chain_for(provider):
        try:
            if prov == "gemini":
                return _gemini_chat(messages, temperature, max_tokens, num_ctx,
                                    model or (GEMINI_MODEL_FAST if fast else None))
            return _ollama_chat(messages, temperature, max_tokens, num_ctx, model)
        except Exception as exc:                      # noqa: BLE001
            last = exc
            LAST_ERROR.update(provider=prov, error=f"{type(exc).__name__}: {exc}")
    raise RuntimeError(f"Không gọi được LLM nào: {last}")


def chat_stream(messages, temperature: float = 0.2, max_tokens: int = 400,
                num_ctx: int = DEFAULT_NUM_CTX,
                model: str | None = None,
                provider: str | None = None) -> Iterator:
    """Sinh dần: yield ("token", str) rồi cuối cùng ("stats", dict).

    Chỉ chuyển provider khi lỗi xảy ra TRƯỚC token đầu tiên — nếu đã phát chữ
    cho người dùng thì thà báo lỗi còn hơn trộn hai câu trả lời khác nhau.
    """
    chain = chain_for(provider)
    for idx, prov in enumerate(chain):
        started = False
        try:
            gen = (_gemini_stream(messages, temperature, max_tokens, num_ctx, model)
                   if prov == "gemini" else
                   _ollama_stream(messages, temperature, max_tokens, num_ctx, model))
            for kind, val in gen:
                if kind == "token":
                    started = True
                yield kind, val
            return
        except Exception as exc:                      # noqa: BLE001
            LAST_ERROR.update(provider=prov, error=f"{type(exc).__name__}: {exc}")
            if started or idx == len(chain) - 1:
                yield "stats", {"provider": prov, "model": model or current_model(),
                                "error": LAST_ERROR["error"]}
                return
