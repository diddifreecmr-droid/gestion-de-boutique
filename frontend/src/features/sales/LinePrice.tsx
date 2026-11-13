import { AlertTriangle } from "lucide-react";
import { formatMoney } from "../../shared/format";
import { AmountField } from "../../shared/ui";
import type { LineDraft } from "./draft";
import { lineTotal, type LineIssues } from "./saleChecks";
import { belowMinimumText } from "./warningText";

export interface LinePriceProps {
  line: LineDraft;
  issues: LineIssues | undefined;
  /** Erreur du prix, déjà filtrée par « montrer les erreurs ». */
  error: string | undefined;
  /** Panier à la ligne (§ 7.4) : « Prix unitaire », base et minimum, total de la ligne. */
  basket: boolean;
  onChange: (unitPrice: number | null) => void;
}

function priceHint(line: LineDraft): string | undefined {
  const { base_price: base, min_price: minimum } = line.article;
  const parts = [
    base === null ? null : `Base ${formatMoney(base)}`,
    minimum === null ? null : `minimum ${formatMoney(minimum)}`,
  ].filter((part): part is string => part !== null);
  return parts.length === 0 ? undefined : parts.join(" · ");
}

/**
 * Prix négocié de la ligne (QC-2 : aucune remise, le prix se discute ligne par ligne) : prix de
 * base pré-rempli et modifiable ; sous le minimum, un avertissement (la vente reste possible,
 * notée au journal, sauf accord exigé par le réglage).
 */
export function LinePrice({ line, issues, error, basket, onChange }: LinePriceProps) {
  const unit = line.article.unit_label;
  const label = basket ? "Prix unitaire" : line.quantity > 1 ? `Prix d'une ${unit}` : "Prix";
  return (
    <>
      <AmountField
        label={label}
        value={line.unitPrice}
        error={error}
        hint={basket ? priceHint(line) : undefined}
        onChange={onChange}
      />
      {issues?.belowMinimum !== undefined && (
        <p className="m-0 flex items-start gap-2 text-body text-warning-text">
          <AlertTriangle aria-hidden="true" className="size-6 shrink-0" />
          <span>{belowMinimumText(issues.belowMinimum, issues.approvalRequired === true)}</span>
        </p>
      )}
      {basket && (
        <p className="m-0 flex items-baseline justify-between gap-4 text-body text-text">
          <span>Ligne</span>
          <strong className="text-lead font-bold tabular-nums">
            {formatMoney(lineTotal(line))}
          </strong>
        </p>
      )}
    </>
  );
}
