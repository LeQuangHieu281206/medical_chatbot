import { NextResponse } from "next/server";

const API_URL = process.env.MEDBOT_API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  let question = "";
  let provider: string | undefined;
  try {
    const body = (await request.json()) as {
      question?: unknown;
      provider?: unknown;
    };
    question = typeof body.question === "string" ? body.question.trim() : "";
    provider =
      typeof body.provider === "string" && body.provider.length <= 20
        ? body.provider
        : undefined;
  } catch {
    return NextResponse.json({ error: "Dữ liệu gửi lên không hợp lệ." }, { status: 400 });
  }

  if (!question) {
    return NextResponse.json({ error: "Câu hỏi đang trống." }, { status: 400 });
  }
  if (question.length > 500) {
    return NextResponse.json(
      { error: "Câu hỏi tối đa 500 ký tự." },
      { status: 400 },
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(provider ? { question, provider } : { question }),
      cache: "no-store",
      signal: request.signal,
    });
  } catch {
    return NextResponse.json(
      {
        error:
          "Không kết nối được dịch vụ trợ lý. Hãy chạy: uvicorn app.api.server:app --port 8000",
      },
      { status: 503 },
    );
  }

  if (!upstream.ok || !upstream.body) {
    const detail = await upstream.text().catch(() => "");
    return new NextResponse(detail || "Dịch vụ trợ lý trả về lỗi.", {
      status: upstream.status === 200 ? 502 : upstream.status,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
