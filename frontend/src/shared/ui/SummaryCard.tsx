import { formatMoney } from "../format";
import { CARD } from "./cardClasses";
import { requireText } from "./controlClasses";

export interface SummaryLine {
  label: string;
  /** Montant en FCFA (entier). */
  amount: number;
}

export interface SummaryCardProps {
  /** Lignes ordinaires : « Total », « Versé »… */
  lines: readonly SummaryLine[];
  /** Ce qui reste dû : en credit-text et --text-amount (§ 2.2, § 6.3). */
  due: number;
  dueLabel?: string;
}

/** Récapitulatif « Total — Versé — Reste à payer » (§ 6.3), montants alignés à droite. */
export function SummaryCard({ lines, due, dueLabel = "Reste à payer" }: SummaryCardProps) {
  requireText("SummaryCard", "dueLabel", dueLabel);
  if (due < 0) {
    throw new Error(`SummaryCard : le reste à payer ne peut pas être négatif (${String(due)})`);
  }
  return (
    <dl className={`${CARD} m-0 flex flex-col gap-2`}>
      {lines.map((line) => (
        <div key={line.label} className="flex items-baseline justify-between gap-4">
          <dt className="text-body text-text-muted">{line.label}</dt>
          <dd className="m-0 text-right text-lead tabular-nums text-text">
            {formatMoney(line.amount)}
          </dd>
        </div>
      ))}
      <div className="flex items-baseline justify-between gap-4 border-t border-border pt-2">
        <dt className="text-label font-semibold text-credit-text">{dueLabel}</dt>
        <dd className="m-0 text-right text-amount font-bold tabular-nums text-credit-text">
          {formatMoney(due)}
        </dd>
      </div>
    </dl>
  );
}
