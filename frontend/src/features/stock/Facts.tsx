import type { ReactNode } from "react";

export interface Fact {
  label: string;
  value: ReactNode;
  /** Ligne de total : séparée au-dessus, en gras. */
  strong?: boolean;
}

/**
 * Lignes « libellé … valeur » d'une carte, valeurs alignées à droite (§ 6.3). Pensé pour
 * 360 px : le libellé passe à la ligne (`min-w-0`, `break-words`) au lieu d'élargir la page.
 */
export function Facts({ facts }: { facts: readonly Fact[] }) {
  return (
    <dl className="m-0 flex flex-col gap-1">
      {facts.map((fact) => (
        <div
          key={fact.label}
          className={`flex items-baseline justify-between gap-4 ${fact.strong === true ? "border-t border-border pt-1" : ""}`}
        >
          <dt
            className={`min-w-0 break-words text-body ${fact.strong === true ? "font-semibold text-text" : "text-text-muted"}`}
          >
            {fact.label}
          </dt>
          <dd
            className={`m-0 min-w-0 break-words text-right tabular-nums text-text ${fact.strong === true ? "text-lead font-bold" : "text-body"}`}
          >
            {fact.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
