"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { streamChat } from "@/lib/chat-stream";
import {
  getServerSnapshot,
  getSnapshot,
  setChatState,
  subscribe,
} from "@/lib/chat-store";
import type { ChatMessage } from "@/lib/types";

function newId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function titleFrom(question: string) {
  const clean = question.replace(/\s+/g, " ").trim();
  return clean.length > 52 ? `${clean.slice(0, 52)}…` : clean;
}

function assistantMessage(): ChatMessage {
  return {
    id: newId(),
    role: "assistant",
    content: "",
    createdAt: Date.now(),
    pending: true,
  };
}

export function useChat() {
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const [isStreaming, setIsStreaming] = useState(false);
  // Model cho lần hỏi này; null = để server dùng mặc định trong .env
  const [provider, setProvider] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const updateMessage = useCallback(
    (convId: string, msgId: string, update: (m: ChatMessage) => ChatMessage) => {
      setChatState((prev) => ({
        ...prev,
        conversations: prev.conversations.map((conv) =>
          conv.id !== convId
            ? conv
            : {
                ...conv,
                messages: conv.messages.map((m) => (m.id === msgId ? update(m) : m)),
              },
        ),
      }));
    },
    [],
  );

  const newChat = useCallback(() => {
    abortRef.current?.abort();
    setChatState((prev) => ({ ...prev, activeId: null }));
  }, []);

  const selectChat = useCallback((id: string) => {
    abortRef.current?.abort();
    setChatState((prev) => ({ ...prev, activeId: id }));
  }, []);

  const deleteChat = useCallback((id: string) => {
    setChatState((prev) => {
      const conversations = prev.conversations.filter((c) => c.id !== id);
      return {
        ...prev,
        conversations,
        activeId:
          prev.activeId === id ? (conversations[0]?.id ?? null) : prev.activeId,
      };
    });
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim().slice(0, 500);
      if (!text || abortRef.current) return;

      const known = state.conversations.some((c) => c.id === state.activeId);
      const convId = known && state.activeId ? state.activeId : newId();
      const userMessage: ChatMessage = {
        id: newId(),
        role: "user",
        content: text,
        createdAt: Date.now(),
      };
      const botMessage = assistantMessage();

      setChatState((prev) => {
        const exists = prev.conversations.some((c) => c.id === convId);
        if (!exists) {
          return {
            ...prev,
            activeId: convId,
            conversations: [
              {
                id: convId,
                title: titleFrom(text),
                createdAt: Date.now(),
                messages: [userMessage, botMessage],
              },
              ...prev.conversations,
            ],
          };
        }
        return {
          ...prev,
          activeId: convId,
          conversations: prev.conversations.map((c) =>
            c.id === convId
              ? { ...c, messages: [...c.messages, userMessage, botMessage] }
              : c,
          ),
        };
      });
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        for await (const event of streamChat(text, controller.signal, provider)) {
          if (event.type === "meta") {
            updateMessage(convId, botMessage.id, (m) => ({
              ...m,
              entities: event.entities ?? m.entities,
              topic: event.topic ?? m.topic,
            }));
          } else if (event.type === "static" || event.type === "text") {
            updateMessage(convId, botMessage.id, (m) => ({
              ...m,
              content: m.content + event.text,
              pending: false,
            }));
          } else if (event.type === "final") {
            updateMessage(convId, botMessage.id, (m) => ({
              ...m,
              sources: event.sources ?? m.sources,
              stats: event.stats ?? m.stats,
              topic: event.topic ?? m.topic,
              error: event.error ?? m.error,
              pending: false,
            }));
          } else if (event.type === "error") {
            updateMessage(convId, botMessage.id, (m) => ({
              ...m,
              content: `${m.content}\n\n${event.message}`.trim(),
              error: true,
              pending: false,
            }));
          }
        }
      } catch (error) {
        if ((error as Error)?.name !== "AbortError") {
          updateMessage(convId, botMessage.id, (m) => ({
            ...m,
            content:
              m.content ||
              "Không kết nối được trợ lý. Vui lòng thử lại sau ít phút.",
            error: true,
            pending: false,
          }));
        } else {
          updateMessage(convId, botMessage.id, (m) => ({ ...m, pending: false }));
        }
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
      }
    },
    [state.activeId, state.conversations, updateMessage, provider],
  );

  const active =
    state.conversations.find((c) => c.id === state.activeId) ?? null;

  return {
    conversations: state.conversations,
    active,
    activeId: state.activeId,
    isStreaming,
    ask,
    stop,
    newChat,
    selectChat,
    deleteChat,
    provider,
    setProvider,
  };
}
