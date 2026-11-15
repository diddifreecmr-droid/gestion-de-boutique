import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

export type SortDirection = "ascending" | "descending";

export interface SortHeaderProps {
  label: string;
  /** Colonne de tri en cours. */
  active: boolean;
  direction: SortDirection;
  onSort: () => void;
  /** Colonne de montants : alignée à droite. */
  numeric?: boolean;
}

/**
 * En-tête de colonne triable (design-system § 7.2, « Coûts et marges », grand écran) : un
 * bouton dans le `<th>`, `aria-sort` sur la colonne active ; cible de 48 px de haut.
 */
export function SortHeader({ label, active, direction, onSort, numeric = false }: SortHeaderProps) {
  const Icon = !active ? ArrowUpDown : direction === "ascending" ? ArrowUp : ArrowDown;
  return (
    <th
      scope="col"
      aria-sort={active ? direction : "none"}
      className={`p-0 align-bottom ${numeric ? "text-right" : "text-left"}`}
    >
      <button
        type="button"
        onClick={onSort}
        className={`inline-flex min-h-12 w-full items-center gap-1 rounded-sm px-2 text-label font-semibold focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid ${numeric ? "justify-end" : "justify-start"} ${active ? "text-text" : "text-text-muted hover:text-text"}`}
      >
        <span>{label}</span>
        <Icon aria-hidden="true" className="size-4 shrink-0" />
      </button>
    </th>
  );
}
