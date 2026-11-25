import { ENTITY_LABELS } from "@/lib/suggestions";
import type { Entity } from "@/lib/types";

export function EntityChips({ entities }: { entities?: Entity[] }) {
  if (!entities || entities.length === 0) return null;

  const unique = Array.from(
    new Map(entities.map((e) => [`${e.text}|${e.label}`, e])).values(),
  ).slice(0, 6);

  return (
    <ul className="mb-3 flex flex-wrap gap-1.5" aria-label="Thực thể y tế nhận diện được">
      {unique.map((entity) => (
        <li
          key={`${entity.text}-${entity.label}`}
          className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-surface-soft px-2.5 py-1 text-[11px] font-medium text-body"
        >
          {entity.text}
          <span className="text-muted">
            {ENTITY_LABELS[entity.label] ?? entity.label}
          </span>
        </li>
      ))}
    </ul>
  );
}
