"use client";

import { useEffect, useRef, useState } from "react";
import { useChat } from "@/hooks/use-chat";
import type { ModelOption } from "@/lib/types";
import { ChatHeader } from "./chat-header";
import { ChatSidebar } from "./chat-sidebar";
import { Composer } from "./composer";
import { EmptyState } from "./empty-state";
import { MessageBubble } from "./message-bubble";

export function ChatApp() {
  const chat = useChat();
  const [menuOpen, setMenuOpen] = useState(false);
  const [models, setModels] = useState<ModelOption[]>([]);
  const scrollRef = useRef<HTMLElement>(null);
  const messages = chat.active?.messages;

  // Danh sách model lấy từ server để menu phản ánh đúng khả năng thật
  // (Gemini chỉ hiện khi đã có GEMINI_API_KEY).
  useEffect(() => {
    let alive = true;
    fetch("/api/models")
      .then((res) => res.json())
      .then((data: { providers?: ModelOption[]; default?: string | null }) => {
        if (!alive) return;
        setModels(data.providers ?? []);
        const fallback = data.default ?? "ollama";
        if (fallback) chat.setProvider((prev) => prev ?? fallback);
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !messages || messages.length === 0) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <div className="flex h-dvh overflow-hidden bg-canvas">
      <ChatSidebar
        conversations={chat.conversations}
        activeId={chat.activeId}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onNew={() => {
          chat.newChat();
          setMenuOpen(false);
        }}
        onSelect={chat.selectChat}
        onDelete={chat.deleteChat}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          title={chat.active?.title ?? "Tư vấn sức khoẻ"}
          onOpenMenu={() => setMenuOpen(true)}
          onNew={chat.newChat}
        />

        <main ref={scrollRef} className="scroll-soft min-h-0 flex-1 overflow-y-auto">
          {!messages || messages.length === 0 ? (
            <EmptyState onPick={(question) => void chat.ask(question)} />
          ) : (
            <div
              role="log"
              aria-live="polite"
              aria-relevant="additions text"
              aria-label="Nội dung cuộc trò chuyện"
              className="mx-auto w-full max-w-[820px] space-y-7 px-4 py-7 sm:px-8 sm:py-9"
            >
              {messages.map((message, index) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  streaming={chat.isStreaming && index === messages.length - 1}
                  showAvatar={index === messages.length - 1}
                />
              ))}
            </div>
          )}
        </main>

        <Composer
          onSend={(question) => void chat.ask(question)}
          onStop={chat.stop}
          isStreaming={chat.isStreaming}
          models={models}
          provider={chat.provider}
          onProviderChange={chat.setProvider}
        />
      </div>
    </div>
  );
}
