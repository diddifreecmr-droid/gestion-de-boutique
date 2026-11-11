import { formatMoney } from "../../shared/format";
import { AmountField, Disclosure, TextField } from "../../shared/ui";
import { CustomerPicker } from "./CustomerPicker";
import { CREDIT_CHOICE, type SaleDraft } from "./draft";
import type { SaleChecks } from "./saleChecks";

export interface SaleExtrasProps {
  shopId: string;
  draft: SaleDraft;
  checks: SaleChecks;
  showErrors: boolean;
  update: (patch: Partial<SaleDraft>) => void;
}

/**
 * « Plus de détails » de la vente (P4) : au comptant, client facultatif, montant remis
 * (monnaie à rendre) et référence du paiement ; toujours, une note.
 */
export function SaleExtras({ shopId, draft, checks, showErrors, update }: SaleExtrasProps) {
  const cash = draft.payment !== null && draft.payment !== CREDIT_CHOICE;
  const single = cash && draft.split === null;
  const shown = (error: string | undefined) => (showErrors ? error : undefined);
  return (
    <Disclosure>
      {cash && (
        <CustomerPicker
          shopId={shopId}
          title="Client (facultatif)"
          value={draft.customer}
          onChange={(customer) => {
            update({ customer });
          }}
          errors={{ name: shown(checks.customerName), phone: shown(checks.customerPhone) }}
        />
      )}
      {single && (
        <>
          <AmountField
            label="Montant remis par le client"
            hint="Facultatif : pour calculer la monnaie"
            value={draft.cashGiven}
            error={shown(checks.cashGiven)}
            onChange={(cashGiven) => {
              update({ cashGiven });
            }}
          />
          {checks.change !== null && (
            <p className="m-0 text-lead text-text" aria-live="polite">
              Monnaie à rendre :{" "}
              <strong className="tabular-nums">{formatMoney(checks.change)}</strong>
            </p>
          )}
          <TextField
            label="Référence du paiement"
            hint="Facultatif : n° de transaction ou de chèque"
            value={draft.reference}
            onChange={(event) => {
              update({ reference: event.target.value });
            }}
          />
        </>
      )}
      <TextField
        label="Note"
        value={draft.note}
        onChange={(event) => {
          update({ note: event.target.value });
        }}
      />
    </Disclosure>
  );
}
