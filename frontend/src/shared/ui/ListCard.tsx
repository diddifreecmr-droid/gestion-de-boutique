import type { ReactNode } from "react";
import { formatMoney } from "../format";
import { PRESSABLE } from "./cardClasses";
import { requireText } from "./controlClasses";

export interface ListCardProps {
  /** Nom accessible de la liste (« Créances »). */
  label: string;
  /** Lignes : des ListCardRow. */
  children: ReactNode;
}

/** Carte de liste (§ 6.3) : séparateur `border` entre les lignes. */
export function ListCard({ label, children }: ListCardProps) {
  requireText("ListCard", "label", label);
  return (
    <ul
      aria-label={label}
      className="m-0 list-none divide-y divide-border overflow-hidden rounded-lg bg-surface p-0 shadow-card"
    >
      {children}
    </ul>
  );
}

export interface ListCardRowProps {
  /** Ligne principale en --text-lead. */
  title: string;
  /** Sous-ligne en text-muted. */
  subtitle?: ReactNode;
  /** Montant à droite (FCFA, entier). */
  amount?: number;
  /** Pastille de statut (un Badge). */
  badge?: ReactNode;
  /** Élément annulé (RG-T03) : la ligne reste, texte barré en text-muted, sauf la pastille. */
  cancelled?: boolean;
  onOpen?: () => void;
}

/** Une ligne d'élément (§ 6.3) : 64 px au moins, montant et pastille à droite. */
export function ListCardRow({
  title,
  subtitle,
  amount,
  badge,
  cancelled = false,
  onOpen,
}: ListCardRowProps) {
  requireText("ListCardRow", "title", title);
  const struck = cancelled ? "text-text-muted line-through" : "";
  const content = (
    <span className="flex min-h-16 items-center gap-4 px-4 py-3">
      <span className="flex min-w-0 flex-1 flex-col">
        <span className={`text-lead text-text ${struck}`}>{title}</span>
        {subtitle !== undefined && (
          <span className={`text-body text-text-muted ${struck}`}>{subtitle}</span>
        )}
      </span>
      {(amount !== undefined || badge !== undefined) && (
        <span className="flex shrink-0 flex-col items-end gap-1">
          {amount !== undefined && (
            <span className={`text-lead font-semibold tabular-nums text-text ${struck}`}>
              {formatMoney(amount)}
            </span>
          )}
          {badge}
        </span>
      )}
    </span>
  );
  return (
    <li>
      {onOpen === undefined ? (
        content
      ) : (
        <button type="button" onClick={onOpen} className={`block ${PRESSABLE}`}>
          {content}
        </button>
      )}
    </li>
  );
}
