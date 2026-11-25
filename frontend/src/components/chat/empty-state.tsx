"use client";

import { ArrowRight, PhoneCall } from "lucide-react";
import { SUGGESTIONS } from "@/lib/suggestions";

export function EmptyState({ onPick }: { onPick: (question: string) => void }) {
  return (
    <div className="mx-auto flex min-h-full w-full max-w-[880px] flex-col px-4 sm:px-8">
      <div className="my-auto py-10 sm:py-14">
        <div className="message-in">
          <h2 className="display max-w-[14ch] text-[clamp(2.25rem,6vw,4rem)] leading-[1.05] tracking-[-0.03em] text-ink">
            Hỏi về sức khoẻ của bạn.
          </h2>
          <p className="mt-4 max-w-[52ch] text-[16px] leading-relaxed text-body">
            Câu trả lời dựa trên tài liệu y khoa và có trích nguồn. Thông tin chỉ
            mang tính tham khảo, không thay thế bác sĩ.
          </p>
        </div>

        <div className="mt-8 grid gap-2.5 sm:mt-10 sm:grid-cols-2">
          {SUGGESTIONS.map((item, index) => (
            <button
              key={item.question}
              type="button"
              onClick={() => onPick(item.question)}
              style={{ animationDelay: `${index * 40}ms` }}
              className="message-in group flex items-start gap-3 rounded-lg border border-hairline bg-surface-card/60 p-4 text-left transition-[transform,background-color,border-color] duration-200 ease-[var(--ease-smooth-out)] hover:-translate-y-0.5 hover:border-primary/40 hover:bg-surface-card active:translate-y-0"
            >
              <span className="mt-0.5 rounded-full bg-canvas px-2.5 py-1 text-[11px] font-medium text-muted">
                {item.tag}
              </span>
              <span className="flex-1 text-[14px] leading-snug text-body-strong">
                {item.question}
              </span>
              <ArrowRight
                className="mt-1 size-4 shrink-0 text-muted transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-primary-deep"
                aria-hidden="true"
              />
            </button>
          ))}
        </div>

        <div className="mt-6 flex items-center gap-3 rounded-lg bg-surface-dark px-4 py-3 text-on-dark">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-surface-dark-elevated">
            <PhoneCall className="size-4 text-amber" aria-hidden="true" />
          </span>
          <p className="text-[13px] leading-snug text-on-dark-soft">
            <span className="font-medium text-on-dark">Trường hợp khẩn cấp:</span> gọi 115
            hoặc đến cơ sở y tế gần nhất, không chờ câu trả lời của chatbot.
          </p>
        </div>
      </div>
    </div>
  );
}
