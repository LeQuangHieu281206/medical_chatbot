"""HTTP bridge for the Next.js chat UI.

Run from the repository root:
    uvicorn app.api.server:app --port 8000

The Next.js app proxies /api/chat to POST /chat here, so the browser never
needs direct access to the model process.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services import llm  # noqa: E402
from app.services.pipeline import MedicalChatbot  # noqa: E402
from app.services.topic_filter import TopicResult  # noqa: E402

log = logging.getLogger("medbot.api")

_bot: MedicalChatbot | None = None
_bot_error: str | None = None
_lock = threading.Lock()


def get_bot() -> MedicalChatbot:
    global _bot, _bot_error
    with _lock:
        if _bot is None:
            bot = MedicalChatbot()
            bot.warmup()
            _bot = bot
            _bot_error = None
        return _bot


def warmup() -> None:
    global _bot_error
    try:
        get_bot()
        log.info("MedicalChatbot ready")
    except Exception as exc:  # keep the API up so /health can explain the failure
        _bot_error = f"{type(exc).__name__}: {exc}"
        log.exception("MedicalChatbot warmup failed")


def _topic(topic: TopicResult | None) -> dict[str, Any] | None:
    if topic is None:
        return None
    return {
        "allowed": topic.allowed,
        "distance": topic.distance,
        "zone": topic.zone,
        "reason": topic.reason,
    }


def _event(event: dict[str, Any]) -> str:
    payload = dict(event)
    topic = _topic(payload.pop("topic", None))
    if topic is not None:
        payload["topic"] = topic
    if "sources" in payload:
        payload["sources"] = [
            {
                "question": source.get("question", ""),
                "link": source.get("link", ""),
                "source": source.get("source", ""),
                "distance": source.get("distance"),
            }
            for source in payload["sources"]
        ]
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    # Chỉ nhận id provider, KHÔNG nhận tên model tự do: tên model do server
    # quyết định để client không thể gọi model đắt tiền hoặc không tồn tại.
    provider: str | None = Field(default=None, max_length=20)


@asynccontextmanager
async def lifespan(_: FastAPI):
    threading.Thread(target=warmup, name="medbot-warmup", daemon=True).start()
    yield


app = FastAPI(title="Medical Chatbot API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/models")
def models() -> dict[str, Any]:
    """Danh sách model cho menu chọn ở giao diện."""
    return {"providers": llm.available_providers(), "default": llm.chain_for(None)[0]}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": _bot is not None,
        "model_ready": _bot is not None,
        "error": _bot_error,
    }


@app.post("/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    question = request.question.strip()
    provider = request.provider or None
    if provider is not None:
        known = {p["id"]: p for p in llm.available_providers()}
        if provider not in known:
            raise HTTPException(status_code=400, detail="Model không hợp lệ.")
        if not known[provider]["ready"]:
            raise HTTPException(
                status_code=400,
                detail=f"{known[provider]['label']} chưa sẵn sàng: cần GEMINI_API_KEY trong .env.",
            )

    def stream():
        try:
            for event in get_bot().ask_stream(question, provider=provider):
                yield _event(event)
        except Exception as exc:
            log.exception("chat stream failed")
            yield _event(
                {
                    "type": "error",
                    "message": (
                        "Xin lỗi, hệ thống gặp sự cố khi tạo câu trả lời "
                        f"({type(exc).__name__}). "
                        + (llm.LAST_ERROR.get("error") or "Hãy kiểm tra Ollama đang chạy.")
                    ),
                }
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api.server:app", host="127.0.0.1", port=8000, reload=False)
