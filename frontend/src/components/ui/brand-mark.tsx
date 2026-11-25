import { cn } from "@/lib/cn";

/** Original medical cross mark — not a copy of any third-party logo. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex size-8 shrink-0 items-center justify-center rounded-[10px] bg-primary text-on-primary",
        className,
      )}
    >
      <svg viewBox="0 0 20 20" className="size-4" fill="none" aria-hidden="true">
        <path
          d="M8 2.75h4v5.25h5.25v4H12v5.25H8V12H2.75V8H8V2.75Z"
          fill="currentColor"
        />
      </svg>
    </span>
  );
}
