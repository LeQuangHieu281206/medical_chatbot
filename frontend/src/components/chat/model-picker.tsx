"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, ChevronUp } from "lucide-react";
import { TextMorph } from "torph/react";
import type { ModelOption } from "@/lib/types";

type Props = {
  models: ModelOption[];
  provider: string | null;
  onChange: (id: string) => void;
  disabled?: boolean;
};

/** "Qwen · qwen3.5:4b" -> "Qwen" */
function shortName(label: string) {
  return label.split("·")[0]?.trim() || label;
}

/**
 * Nút chọn model nằm trong thanh nhập, kiểu Gemini: một viên thuốc (pill) mở
 * ra danh sách ngay phía trên.
 *
 * Dùng <button role="option"> thay vì <select> để hiện được mô tả từng model,
 * nhưng vẫn giữ bàn phím: mũi tên di chuyển, Enter chọn, Escape đóng.
 */
export function ModelPicker({ models, provider, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Dự phòng khi chưa đọc được danh sách model (backend chưa chạy): vẫn phải
  // hiện nút, không được im lặng biến mất — người dùng sẽ tưởng tính năng hỏng.
  const options: ModelOption[] =
    models.length > 0
      ? models
      : [
          {
            id: "ollama",
            label: "Qwen · qwen3.5:4b",
            model: "qwen3.5:4b",
            ready: true,
            note: "",
          },
          {
            id: "gemini",
            label: "Gemini · gemini-3.5-flash",
            model: "gemini-3.5-flash",
            ready: true,
            note: "",
          },
        ];

  const value = provider ?? options[0]?.id ?? "";
  const current = options.find((m) => m.id === value);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Mở menu thì đưa focus vào lựa chọn đang dùng, để dòng được tô sáng
  // trùng với dấu ✓ thay vì luôn nhảy về dòng đầu (Qwen).
  useEffect(() => {
    if (!open) return;
    const menu = menuRef.current;
    if (!menu) return;
    const active =
      menu.querySelector<HTMLButtonElement>(
        '[role="option"][aria-selected="true"]:not(:disabled)',
      ) ?? menu.querySelector<HTMLButtonElement>('[role="option"]:not(:disabled)');
    active?.focus();
  }, [open]);

  function onMenuKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLButtonElement>(
        '[role="option"]:not(:disabled)',
      ) ?? [],
    );
    if (items.length === 0) return;
    const index = items.indexOf(document.activeElement as HTMLButtonElement);
    const step = event.key === "ArrowDown" ? 1 : -1;
    items[(index + step + items.length) % items.length]?.focus();
  }

  return (
    <div ref={wrapRef} className="relative shrink-0">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Model trả lời: ${current?.label ?? value}. Bấm để đổi.`}
        title={current?.label}
        className="flex shrink-0 items-center gap-1 rounded-full border border-hairline bg-surface-soft px-2.5 py-1.5 text-[12px] font-medium text-ink transition-colors duration-150 hover:border-primary-deep hover:text-primary-deep focus:border-primary-deep focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      >
        <TextMorph
          as="span"
          locale="vi"
          duration={320}
          className="block max-w-[92px] truncate"
        >
          {shortName(current?.label ?? value)}
        </TextMorph>
        {open ? (
          <ChevronUp className="size-3.5 opacity-60" aria-hidden="true" />
        ) : (
          <ChevronDown className="size-3.5 opacity-60" aria-hidden="true" />
        )}
      </button>

      {open ? (
        <div
          ref={menuRef}
          role="listbox"
          aria-label="Chọn model trả lời"
          onKeyDown={onMenuKeyDown}
          className="absolute bottom-full right-0 z-20 mb-2 w-[212px] rounded-xl border border-hairline bg-canvas p-1.5 shadow-[0_8px_28px_rgba(20,20,19,0.13)]"
        >
          {options.map((option) => {
            const selected = option.id === value;
            return (
              <button
                key={option.id}
                type="button"
                role="option"
                aria-selected={selected}
                disabled={!option.ready}
                onClick={() => {
                  onChange(option.id);
                  setOpen(false);
                  buttonRef.current?.focus();
                }}
                className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left transition-colors duration-150 hover:bg-surface-card focus:bg-surface-card focus:outline-none disabled:cursor-not-allowed disabled:opacity-45 aria-selected:bg-surface-soft"
              >
                <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink">
                  {shortName(option.label)}
                  <span className="ml-1.5 font-normal text-muted">{option.model}</span>
                </span>
                {selected ? (
                  <Check className="size-3.5 shrink-0 text-primary-deep" aria-hidden="true" />
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
