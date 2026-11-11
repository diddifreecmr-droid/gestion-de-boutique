import { useId } from "react";
import type { SaleResult } from "../../core/gateways/salesContract";
import { formatDate, formatMoney, formatTime } from "../../shared/format";
import { SummaryCard } from "../../shared/ui";
import { locationName, modeName, sellerName, type SaleRefs } from "./saleRefs";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-text-muted">{label}</dt>
      <dd className="m-0 break-words text-text">{value}</dd>
    </>
  );
}

/** Faits de la vente (date, lieu, vendeur, conditions de crédit, note) puis paiements et totaux. */
export function SaleFacts({ sale, refs }: { sale: SaleResult; refs: SaleRefs }) {
  const paymentsId = useId();
  return (
    <>
      <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg bg-surface p-4 text-body shadow-card">
        <Fact label="Date" value={`${formatDate(sale.sold_on)} à ${formatTime(sale.sold_at)}`} />
        <Fact label="Lieu de vente" value={locationName(refs, sale.location_id)} />
        {refs.role === "owner" && <Fact label="Vendeur" value={sellerName(refs, sale.seller_id)} />}
        {sale.credit?.reminder_on != null && (
          <Fact label="Date de rappel" value={formatDate(sale.credit.reminder_on)} />
        )}
        {sale.credit?.terms != null && <Fact label="Conditions" value={sale.credit.terms} />}
        {sale.note !== null && <Fact label="Note" value={sale.note} />}
      </dl>
      <section aria-labelledby={paymentsId} className="flex flex-col gap-2">
        <h2 id={paymentsId} className="m-0 text-title-sm font-semibold text-text">
          Paiements
        </h2>
        {sale.payments.length === 0 ? (
          <p className="m-0 text-body text-text-muted">Aucun paiement à la vente.</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-1 p-0 text-body text-text">
            {sale.payments.map((payment) => (
              <li key={payment.id} className="flex justify-between gap-4">
                <span className="break-words">
                  {modeName(refs, payment.mode_id)}
                  {payment.reference === null ? "" : ` (${payment.reference})`}
                </span>
                <span className="shrink-0 tabular-nums">{formatMoney(payment.amount)}</span>
              </li>
            ))}
          </ul>
        )}
        <SummaryCard
          lines={[
            { label: "Total", amount: sale.total },
            { label: "Versé", amount: sale.paid },
          ]}
          due={sale.remaining}
        />
      </section>
    </>
  );
}
