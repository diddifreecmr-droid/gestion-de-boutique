import type { Receivable } from "../../core/gateways/receivablesContract";
import { formatDate, formatMoney } from "../../shared/format";
import { SummaryCard } from "../../shared/ui";
import { bandLabel, daysText } from "./labels";
import { memberName, type References } from "./references";
import { originText } from "./receivableRules";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-text-muted">{label}</dt>
      <dd className="m-0 break-words text-text">{value}</dd>
    </>
  );
}

/** Mise en perte (UC-CRE-09) ou annulation de la vente liée, en clair. */
function closingText(refs: References, receivable: Receivable): string | null {
  const off = receivable.write_off;
  if (off !== null) {
    return `Passée en perte le ${formatDate(off.on)} par ${memberName(refs, off.by)} — motif : ${off.reason}`;
  }
  if (receivable.cancelled_on !== null) {
    return `Vente liée annulée le ${formatDate(receivable.cancelled_on)}`;
  }
  return null;
}

/** Faits de la créance : montants (reste en violet), client, origine, dates, responsable. */
export function ReceivableFacts({
  refs,
  receivable,
}: {
  refs: References;
  receivable: Receivable;
}) {
  const closing = closingText(refs, receivable);
  return (
    <>
      <SummaryCard
        lines={[
          { label: "Montant initial", amount: receivable.initial_amount },
          { label: "Déjà versé", amount: receivable.total_paid },
        ]}
        due={receivable.remaining}
      />
      {closing !== null && <p className="m-0 text-body text-text">{closing}</p>}
      <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg bg-surface p-4 text-body shadow-card">
        <Fact label="Client" value={receivable.customer.name} />
        <Fact label="Téléphone" value={receivable.customer.phone} />
        <Fact label="Origine" value={originText(receivable)} />
        {receivable.sale_total !== null && receivable.paid_at_sale > 0 && (
          <Fact label="Acompte à la vente" value={formatMoney(receivable.paid_at_sale)} />
        )}
        <Fact label="Ouverte le" value={formatDate(receivable.opened_on)} />
        <Fact
          label="Ancienneté"
          value={`${daysText(receivable.seniority_days)} (${bandLabel(receivable.seniority_band)})`}
        />
        <Fact
          label="Dernier versement"
          value={
            receivable.last_installment_on === null
              ? "Aucun"
              : formatDate(receivable.last_installment_on)
          }
        />
        <Fact
          label="Vendeur responsable"
          value={memberName(refs, receivable.responsible_seller_id)}
        />
        {receivable.terms !== null && <Fact label="Conditions" value={receivable.terms} />}
      </dl>
    </>
  );
}
