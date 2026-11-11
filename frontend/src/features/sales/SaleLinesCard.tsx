import { useId } from "react";
import type { SaleResult, SoldDetail } from "../../core/gateways/salesContract";
import { formatMoney, formatQuantity } from "../../shared/format";
import type { SaleRole } from "./salesNav";
import { moneyOrNot, ownerCosts } from "./saleView";

function detailText(detail: SoldDetail): string {
  const parts: [string, string | null][] = [
    ["Couleur", detail.color],
    ["Châssis", detail.chassis_number],
    ["Moteur", detail.engine_number],
    ["Taille", detail.size],
  ];
  return parts
    .filter((part): part is [string, string] => part[1] !== null && part[1] !== "")
    .map(([label, value]) => `${label} : ${value}`)
    .join(" · ");
}

/** Lignes de la fiche : article, détails, quantité × prix, total ; coûts pour le propriétaire. */
export function SaleLinesCard({ sale, role }: { sale: SaleResult; role: SaleRole }) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Articles
      </h2>
      {sale.lines.map((line, index) => {
        const costs = ownerCosts(role, line);
        return (
          <div
            key={index}
            className="flex flex-col gap-1 border-t border-border pt-4 first:border-0 first:pt-0"
          >
            <p className="m-0 flex items-baseline justify-between gap-4 text-lead text-text">
              <span className="break-words">{line.article_name}</span>
              <strong className="shrink-0 tabular-nums">{formatMoney(line.line_total)}</strong>
            </p>
            <p className="m-0 text-body text-text-muted">
              {formatQuantity(line.quantity)} × {formatMoney(line.unit_price)}
            </p>
            {line.details.map((detail, at) => (
              <p key={at} className="m-0 break-words text-body text-text-muted">
                {detailText(detail)}
              </p>
            ))}
            {costs !== null && (
              <dl className="m-0 grid grid-cols-2 gap-x-4 text-body text-text">
                <dt className="text-text-muted">Dernier coût figé</dt>
                <dd className="m-0 text-right tabular-nums">{moneyOrNot(costs.lastCost)}</dd>
                <dt className="text-text-muted">CMP figé</dt>
                <dd className="m-0 text-right tabular-nums">{moneyOrNot(costs.wac)}</dd>
                <dt className="text-text-muted">Marge</dt>
                <dd className="m-0 text-right tabular-nums">{moneyOrNot(costs.margin)}</dd>
                <dt className="text-text-muted">Marge (CMP)</dt>
                <dd className="m-0 text-right tabular-nums">{moneyOrNot(costs.marginWac)}</dd>
              </dl>
            )}
          </div>
        );
      })}
    </section>
  );
}
