import type { PaymentMode } from "../../core/gateways/catalogContract";
import { AmountField, ChoiceChips, Disclosure, SummaryCard, TextField } from "../../shared/ui";
import { CustomerPicker } from "./CustomerPicker";
import type { SaleDraft } from "./draft";
import { FieldMessage } from "./FieldMessage";
import type { SaleChecks } from "./saleChecks";

export interface CreditSectionProps {
  shopId: string;
  modes: readonly PaymentMode[];
  draft: SaleDraft;
  checks: SaleChecks;
  showErrors: boolean;
  update: (patch: Partial<SaleDraft>) => void;
}

/**
 * Vente à crédit (UC-VEN-02) : client obligatoire (H20), acompte (0 accepté) et son mode,
 * rappel et conditions facultatifs, puis « Total — Versé — Reste à payer ».
 */
export function CreditSection({
  shopId,
  modes,
  draft,
  checks,
  showErrors,
  update,
}: CreditSectionProps) {
  const shown = (error: string | undefined) => (showErrors ? error : undefined);
  const deposit = draft.deposit ?? 0;
  return (
    <>
      <CustomerPicker
        shopId={shopId}
        title="Client"
        value={draft.customer}
        onChange={(customer) => {
          update({ customer });
        }}
        errors={{
          customer: shown(checks.customer),
          name: shown(checks.customerName),
          phone: shown(checks.customerPhone),
        }}
      />
      <AmountField
        label="Acompte versé aujourd'hui"
        hint="Laissez vide ou 0 si rien n'est versé"
        value={draft.deposit}
        error={checks.deposit}
        onChange={(value) => {
          update({ deposit: value });
        }}
      />
      {deposit > 0 && (
        <ChoiceChips
          label="Mode de l'acompte"
          options={modes.map((mode) => ({ value: mode.id, label: mode.label }))}
          value={draft.depositMode}
          onChange={(depositMode) => {
            update({ depositMode });
          }}
        />
      )}
      {showErrors && checks.depositMode !== undefined && <FieldMessage text={checks.depositMode} />}
      <Disclosure label="Plus de détails : rappel, conditions">
        <TextField
          label="Date de rappel"
          type="date"
          value={draft.reminderOn}
          onChange={(event) => {
            update({ reminderOn: event.target.value });
          }}
        />
        <TextField
          label="Conditions convenues"
          hint="Ex. 100 000 par mois"
          value={draft.terms}
          onChange={(event) => {
            update({ terms: event.target.value });
          }}
        />
      </Disclosure>
      <SummaryCard
        lines={[
          { label: "Total", amount: checks.total },
          { label: "Versé", amount: checks.paid },
        ]}
        due={checks.remaining}
      />
    </>
  );
}
