"use client";

import { BookOpen, ChevronDown, ExternalLink } from "lucide-react";
import type { Source } from "@/lib/types";

function safeHref(link?: string) {
  if (!link) return null;
  try {
    const url = new URL(link);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

export function SourceList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;

  return (
    <details className="group mt-4 rounded-lg border border-hairline bg-surface-soft/60">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3.5 py-2.5 text-[13px] font-medium text-body-strong [&::-webkit-details-marker]:hidden">
        <BookOpen className="size-4 text-primary" aria-hidden="true" />
        Nguồn tham khảo
        <span className="rounded-full bg-surface-card px-2 py-0.5 text-[11px] font-medium text-muted">
          {sources.length}
        </span>
        <ChevronDown
          className="ml-auto size-4 text-muted transition-transform duration-200 group-open:rotate-180"
          aria-hidden="true"
        />
      </summary>
      <ol className="space-y-0 border-t border-hairline-soft px-3.5 py-2.5">
        {sources.map((source, index) => {
          const href = safeHref(source.link);
          const label = source.question || source.source || "Tài liệu y khoa";
          return (
            <li
              key={`${label}-${index}`}
              className="flex items-start gap-2.5 border-b border-hairline-soft py-2.5 last:border-b-0"
            >
              <span
                className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-canvas text-[11px] font-medium text-muted"
                aria-hidden="true"
              >
                {index + 1}
              </span>
              {href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group/link flex items-start gap-1.5 text-[13px] leading-snug text-body transition-colors duration-150 hover:text-primary-deep"
                >
                  <span>{label}</span>
                  <ExternalLink
                    className="mt-0.5 size-3.5 shrink-0 text-muted group-hover/link:text-primary-deep"
                    aria-hidden="true"
                  />
                </a>
              ) : (
                <span className="text-[13px] leading-snug text-body">{label}</span>
              )}
            </li>
          );
        })}
      </ol>
    </details>
  );
}
