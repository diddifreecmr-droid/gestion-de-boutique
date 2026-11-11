import type { Purchase } from "../../core/gateways/purchasingContract";
import { formatDate, formatMoney } from "../../shared/format";
import { SummaryCard } from "../../shared/ui";
import { remainingOf } from "./correctionRule";
import { modeName, type References } from "./references";

/**
 * Paiements notés au fournisseur (UC-ACH-06, simple repère) : « Total — Payé — Reste à payer »
 * puis chaque paiement (date, montant, mode, référence). Un achat annulé n'a plus rien à payer.
 */
export function PaymentsCard({ refs, purchase }: { refs: References; purchase: Purchase }) {
  const cancelled = purchase.status === "cancelled";
  return (
    <section aria-label="Paiements" className="flex flex-col gap-2">
      <h2 className="m-0 text-title-sm font-semibold text-text">Paiements</h2>
      <SummaryCard
        lines={[
          { label: "Total marchandise", amount: purchase.merchandise_total },
          { label: "Total des frais", amount: purchase.fees_total },
          { label: "Total de l'achat", amount: purchase.total },
          { label: "Payé", amount: purchase.paid },
        ]}
        due={cancelled ? 0 : remainingOf(purchase)}
      />
      {purchase.payments.length === 0 ? (
        <p className="m-0 text-body text-text-muted">Aucun paiement noté.</p>
      ) : (
        <ul
          aria-label="Paiements notés"
          className="m-0 list-none divide-y divide-border overflow-hidden rounded-lg bg-surface p-0 shadow-card"
        >
          {purchase.payments.map((payment) => (
            <li
              key={payment.id}
              className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3"
            >
              <span className="flex min-w-0 flex-col">
                <span className="text-lead text-text">{formatDate(payment.paid_on)}</span>
                <span className="break-words text-body text-text-muted">
                  {[modeName(refs, payment.mode_id), payment.reference ?? ""]
                    .filter((part) => part !== "")
                    .join(" · ")}
                </span>
              </span>
              <span className="text-lead font-semibold tabular-nums text-text">
                {formatMoney(payment.amount)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
