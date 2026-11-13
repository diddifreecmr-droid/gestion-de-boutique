import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { PRESSABLE } from "./cardClasses";
import { requireText } from "./controlClasses";

export interface ListCardDetailRowProps {
  /** Ligne principale en --text-lead (nom de l'article). */
  title: string;
  /** Sous-ligne en text-muted. */
  subtitle?: ReactNode;
  /** Chiffre à droite, déjà mis en forme (« 12 », « 2,5 m »). */
  value?: string;
  /** Libellé du chiffre, lu avec lui (« En stock »). */
  valueLabel?: string;
  /** Pastille de statut (un Badge), sous le chiffre. */
  badge?: ReactNode;
  /** Détail montré sous la ligne une fois ouverte (lieux, prix, actions). */
  children: ReactNode;
}

/**
 * Ligne de `ListCard` qui se déplie sur place (§ 6.3) : l'essentiel sur la ligne (≥ 64 px),
 * le détail à un appui, sans changer d'écran. Motif ARIA « disclosure » ; le détail n'est
 * monté qu'ouvert (longue liste = DOM léger), son conteneur existe toujours (`aria-controls`).
 */
export function ListCardDetailRow({
  title,
  subtitle,
  value,
  valueLabel,
  badge,
  children,
}: ListCardDetailRowProps) {
  requireText("ListCardDetailRow", "title", title);
  if (valueLabel !== undefined && value === undefined) {
    throw new Error("ListCardDetailRow : valueLabel sans value");
  }
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <li>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => {
          setOpen((current) => !current);
        }}
        className={`block ${PRESSABLE}`}
      >
        <span className="flex min-h-16 items-center gap-4 px-4 py-3">
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="break-words text-lead text-text">{title}</span>
            {subtitle !== undefined && (
              <span className="text-body text-text-muted">{subtitle}</span>
            )}
          </span>
          {(value !== undefined || badge !== undefined) && (
            <span className="flex shrink-0 flex-col items-end gap-1">
              {value !== undefined && (
                <span className="flex items-baseline gap-1">
                  {valueLabel !== undefined && (
                    <span className="text-body text-text-muted">{valueLabel}</span>
                  )}
                  <span className="text-lead font-semibold tabular-nums text-text">{value}</span>
                </span>
              )}
              {badge}
            </span>
          )}
          <ChevronDown
            aria-hidden="true"
            className={`size-6 shrink-0 text-primary transition-transform duration-(--duration-fast) ease-out ${open ? "rotate-180" : ""}`}
          />
        </span>
      </button>
      <div id={panelId} hidden={!open} className="flex flex-col gap-4 px-4 pb-4">
        {open && children}
      </div>
    </li>
  );
}
