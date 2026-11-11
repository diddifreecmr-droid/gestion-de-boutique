import { useId } from "react";
import type { SaleReturn } from "../../../core/gateways/returnsContract";
import { formatDate, formatMoney, formatQuantity } from "../../../shared/format";
import { Badge, Button } from "../../../shared/ui";
import { modeName, sellerName, type SaleRefs } from "../saleRefs";
import { moneyOrNot, ownerReturnMargin } from "../saleView";

export interface SaleReturnsCardProps {
  returns: readonly SaleReturn[];
  refs: SaleRefs;
  onOpenSale: (id: string) => void;
}

/** Retours et échanges d'une vente, sur sa fiche (UC-VEN-09). */
export function SaleReturnsCard({ returns, refs, onOpenSale }: SaleReturnsCardProps) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Retours
      </h2>
      {returns.map((made) => {
        const margin = ownerReturnMargin(refs.role, made);
        const exchange = made.exchange_sale_id;
        return (
          <div
            key={made.id}
            className="flex flex-col gap-1 border-t border-border pt-4 first:border-0 first:pt-0"
          >
            <p className="m-0 flex flex-wrap items-center justify-between gap-2 text-lead text-text">
              <span>
                {exchange === null ? "Retour" : "Échange"} du {formatDate(made.returned_on)}
              </span>
              <strong className="tabular-nums">{formatMoney(made.amount)}</strong>
            </p>
            {made.lines.map((line) => (
              <p key={line.line} className="m-0 break-words text-body text-text">
                {formatQuantity(line.quantity)} × {line.article_name}
                {line.chassis.length > 0 && ` — châssis ${line.chassis.join(", ")}`}{" "}
                {line.condition === "damaged" ? (
                  <Badge status="danger">Abîmé</Badge>
                ) : (
                  <Badge status="success">Vendable</Badge>
                )}
              </p>
            ))}
            <p className="m-0 text-body text-text-muted">
              Motif : {made.reason} — par {sellerName(refs, made.created_by)}
            </p>
            {made.refund !== null && (
              <p className="m-0 text-body text-text">
                Remboursé : {formatMoney(made.refund.amount)} ({modeName(refs, made.refund.mode_id)}
                ) le {formatDate(made.refund.refunded_on)}
              </p>
            )}
            {made.credit_reduction > 0 && (
              <p className="m-0 text-body text-text">
                Baisse de la créance : {formatMoney(made.credit_reduction)}
              </p>
            )}
            {margin !== undefined && (
              <p className="m-0 text-body text-text">Marge retirée : {moneyOrNot(margin)}</p>
            )}
            {exchange !== null && (
              <Button
                variant="ghost"
                onClick={() => {
                  onOpenSale(exchange);
                }}
              >
                Voir la nouvelle vente
              </Button>
            )}
          </div>
        );
      })}
    </section>
  );
}
