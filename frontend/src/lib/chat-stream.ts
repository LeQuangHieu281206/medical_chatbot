import type { ChatEvent } from "./types";

/**
 * Reads the chat SSE stream from our own /api/chat route.
 * Frames are `data: <json>\n\n` with the event type inside the JSON.
 */
export async function* streamChat(
  question: string,
  signal?: AbortSignal,
  provider?: string | null,
): AsyncGenerator<ChatEvent> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(provider ? { question, provider } : { question }),
    signal,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `Máy chủ trả về lỗi ${response.status}.`);
  }
  if (!response.body) throw new Error("Máy chủ không trả về dữ liệu.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n");

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const payload = frame
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");

        if (payload) {
          try {
            yield JSON.parse(payload) as ChatEvent;
          } catch {
            // Ignore keep-alive or malformed frames instead of killing the stream.
          }
        }
        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}
