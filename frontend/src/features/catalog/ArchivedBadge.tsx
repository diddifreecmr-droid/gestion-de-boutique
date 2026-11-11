import { Archive } from "lucide-react";

/**
 * Pastille « Archivé » (design-system.md § 6.4 : mot + icône, la couleur ne suffit pas).
 * Statut neutre absent de `Badge` : mêmes dimensions, couleurs `bg` / `text-muted`.
 */
export function ArchivedBadge() {
  return (
    <span className="inline-flex min-h-7 items-center gap-1 rounded-sm border border-border-strong bg-bg px-2 text-label font-semibold whitespace-nowrap text-text-muted">
      <Archive aria-hidden="true" className="size-6 shrink-0" />
      <span>Archivé</span>
    </span>
  );
}
