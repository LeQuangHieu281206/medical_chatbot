import type { Conversation } from "./types";

export type ChatState = {
  conversations: Conversation[];
  activeId: string | null;
};

const STORE_KEY = "medbot.chat.v2";
const EMPTY: ChatState = { conversations: [], activeId: null };

let cache: ChatState = EMPTY;
let loaded = false;
const listeners = new Set<() => void>();

function read(): ChatState {
  if (loaded) return cache;
  loaded = true;
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<ChatState>;
      if (Array.isArray(parsed.conversations)) {
        cache = {
          conversations: parsed.conversations,
          activeId:
            typeof parsed.activeId === "string" ? parsed.activeId : null,
        };
      }
    }
  } catch {
    // A corrupt or unavailable store must not block the chat.
  }
  return cache;
}

let persistTimer: ReturnType<typeof setTimeout> | null = null;

function persistNow(state: ChatState) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
  } catch {
    // Quota or private mode: the session still works in memory.
  }
}

// Streamed tokens arrive fast; batch the disk write instead of one per token.
function persist(state: ChatState) {
  if (persistTimer) clearTimeout(persistTimer);
  persistTimer = setTimeout(() => persistNow(state), 250);
}

if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => persistNow(cache));
}

export function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot() {
  return read();
}

export function getServerSnapshot() {
  return EMPTY;
}

export function setChatState(update: (state: ChatState) => ChatState) {
  cache = update(read());
  persist(cache);
  listeners.forEach((listener) => listener());
}
