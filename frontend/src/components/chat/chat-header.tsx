"use client";

import { Menu, Plus } from "lucide-react";

type Props = {
  title: string;
  onOpenMenu: () => void;
  onNew: () => void;
};

export function ChatHeader({ title, onOpenMenu, onNew }: Props) {
  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b border-hairline bg-canvas/85 px-4 backdrop-blur-md sm:px-6">
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="Mở thanh bên"
        className="flex size-10 items-center justify-center rounded-md text-body transition-colors duration-150 hover:bg-surface-card hover:text-ink lg:hidden"
      >
        <Menu className="size-5" aria-hidden="true" />
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-sm font-medium text-ink">{title}</h1>
        <p className="hidden text-[12px] text-muted sm:block">
          Thông tin tham khảo, không thay thế bác sĩ
        </p>
      </div>

      <button
        type="button"
        onClick={onNew}
        aria-label="Cuộc trò chuyện mới"
        className="flex size-10 items-center justify-center rounded-md border border-hairline bg-canvas text-ink transition-colors duration-150 hover:border-primary-deep hover:text-primary-deep lg:hidden"
      >
        <Plus className="size-4" aria-hidden="true" />
      </button>
    </header>
  );
}
