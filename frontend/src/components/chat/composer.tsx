"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Square } from "lucide-react";
import { ThinkingOrb } from "thinking-orbs";
import type { ModelOption } from "@/lib/types";
import { cn } from "@/lib/cn";
import { ModelPicker } from "./model-picker";

type Props = {
  onSend: (question: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  models: ModelOption[];
  provider: string | null;
  onProviderChange: (id: string) => void;
};

/**
 * Hai khối xếp chồng trong cùng một ô:
 * - khối nhập (cao) khi rảnh
 * - khối "đang suy nghĩ" (thấp, có orb + chữ nhấp nháy) khi đang trả lời
 * Chỉ một khối có chiều cao khác 0 tại mỗi thời điểm, nên thanh tự co/bung.
 */
const block = (visible: boolean) =>
  cn(
    "grid overflow-hidden transition-[grid-template-rows,opacity] duration-300 ease-out",
    visible ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
  );

export function Composer({
  onSend,
  onStop,
  isStreaming,
  models,
  provider,
  onProviderChange,
}: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 168)}px`;
  }, [value]);

  function submit() {
    const question = value.trim();
    if (!question || isStreaming) return;
    onSend(question);
    setValue("");
  }

  return (
    <div className="shrink-0 px-3 pb-3 sm:px-6 sm:pb-5">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        className="mx-auto w-full max-w-[820px]"
      >
        <div
          className={cn(
            "flex items-center gap-2 rounded-[18px] border bg-canvas p-2.5 shadow-[0_1px_3px_rgba(20,20,19,0.05)]",
            "transition-[border-color,box-shadow] duration-200",
            isStreaming
              ? "border-hairline"
              : "focus-within:border-primary focus-within:shadow-[0_0_0_3px_rgba(204,120,92,0.14)]",
          )}
        >
          <div className="min-w-0 flex-1">
            {/* Khối nhập */}
            <div className={block(!isStreaming)} aria-hidden={isStreaming}>
              <div className="min-h-0 overflow-hidden">
                <label htmlFor="chat-input" className="sr-only">
                  Nhập câu hỏi về sức khoẻ
                </label>
                <textarea
                  id="chat-input"
                  ref={textareaRef}
                  rows={1}
                  value={value}
                  maxLength={500}
                  tabIndex={isStreaming ? -1 : 0}
                  onChange={(event) => setValue(event.target.value)}
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.shiftKey &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault();
                      submit();
                    }
                  }}
                  placeholder="Nhập câu hỏi về sức khoẻ…"
                  className="scroll-soft max-h-[168px] min-h-[64px] w-full resize-none bg-transparent px-1.5 py-1.5 text-[15px] leading-relaxed text-ink outline-none placeholder:text-muted"
                />
              </div>
            </div>

            {/* Khối đang suy nghĩ */}
            <div className={block(isStreaming)} aria-hidden={!isStreaming}>
              <div className="min-h-0 overflow-hidden">
                <div className="flex items-center gap-2.5 px-1.5 py-[15px]">
                  <ThinkingOrb
                    state="working"
                    size={20}
                    theme="light"
                    aria-label="Đang soạn câu trả lời"
                  />
                  <span className="thinking-fade text-[14px] text-muted">
                    Đang suy nghĩ…
                  </span>
                </div>
              </div>
            </div>
          </div>

          <ModelPicker
            models={models}
            provider={provider}
            onChange={onProviderChange}
            disabled={isStreaming}
          />

          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Dừng trả lời"
              className="flex size-10 shrink-0 items-center justify-center rounded-md border border-hairline bg-surface-soft text-ink transition-colors duration-150 hover:border-primary-deep hover:text-primary-deep"
            >
              <Square className="size-3.5 fill-current" aria-hidden="true" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!value.trim()}
              aria-label="Gửi câu hỏi"
              className="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary-active text-on-primary transition-colors duration-150 hover:bg-primary-deep disabled:bg-primary-disabled disabled:text-muted"
            >
              <Send className="size-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
