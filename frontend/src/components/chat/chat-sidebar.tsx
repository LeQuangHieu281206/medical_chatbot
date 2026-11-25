"use client";

import { MessageSquareText, Plus, Trash2, X } from "lucide-react";
import { BrandMark } from "@/components/ui/brand-mark";
import type { Conversation } from "@/lib/types";
import { cn } from "@/lib/cn";

type Props = {
  conversations: Conversation[];
  activeId: string | null;
  open: boolean;
  onClose: () => void;
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
};

export function ChatSidebar({
  conversations,
  activeId,
  open,
  onClose,
  onNew,
  onSelect,
  onDelete,
}: Props) {
  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-40 bg-ink/25 backdrop-blur-[2px] transition-opacity duration-200 lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />
      <aside
        aria-label="Lịch sử trò chuyện"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[300px] shrink-0 flex-col border-r border-hairline bg-surface-soft transition-transform duration-300 ease-[var(--ease-smooth-out)] lg:static lg:z-auto lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center justify-between gap-2 border-b border-hairline-soft px-5">
          <div className="flex items-center gap-2.5">
            <BrandMark />
            <p className="display text-[19px] tracking-[-0.02em] text-ink">
              Trợ lý Y tế
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng thanh bên"
            className="flex size-9 items-center justify-center rounded-md text-muted transition-colors duration-150 hover:bg-surface-card hover:text-ink focus-visible:outline-2 lg:hidden"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>

        <div className="px-4 pt-4">
          <button
            type="button"
            onClick={onNew}
            className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-primary-active px-4 text-sm font-medium text-on-primary transition-colors duration-150 hover:bg-primary-deep active:bg-primary-deep"
          >
            <Plus className="size-4" aria-hidden="true" />
            Cuộc trò chuyện mới
          </button>
        </div>

        <div className="mt-5 flex min-h-0 flex-1 flex-col">
          <p className="px-5 text-[11px] font-medium text-muted">Gần đây</p>
          <nav className="scroll-soft mt-2 flex-1 overflow-y-auto px-3 pb-4">
            {conversations.length === 0 ? (
              <p className="px-2 py-3 text-sm leading-relaxed text-muted">
                Chưa có cuộc trò chuyện nào. Đặt câu hỏi đầu tiên để bắt đầu.
              </p>
            ) : (
              <ul className="space-y-0.5">
                {conversations.map((conv) => {
                  const active = conv.id === activeId;
                  return (
                    <li key={conv.id} className="group relative">
                      <button
                        type="button"
                        onClick={() => {
                          onSelect(conv.id);
                          onClose();
                        }}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "flex w-full items-center gap-2.5 rounded-md py-2.5 pr-10 pl-2.5 text-left text-sm transition-colors duration-150",
                          active
                            ? "bg-surface-card text-ink"
                            : "text-body hover:bg-surface-card/70 hover:text-ink",
                        )}
                      >
                        <MessageSquareText
                          className={cn(
                            "size-4 shrink-0",
                            active ? "text-primary-deep" : "text-muted",
                          )}
                          aria-hidden="true"
                        />
                        <span className="truncate">{conv.title}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(conv.id)}
                        aria-label={`Xoá cuộc trò chuyện: ${conv.title}`}
                        className="absolute top-1/2 right-1.5 flex size-8 -translate-y-1/2 items-center justify-center rounded-sm text-muted opacity-0 transition-opacity duration-150 group-hover:opacity-100 hover:bg-surface-strong hover:text-error focus-visible:opacity-100"
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </nav>
        </div>
      </aside>
    </>
  );
}
