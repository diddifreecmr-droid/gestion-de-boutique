import { Banknote, Split } from "lucide-react";
import type { PaymentMode } from "../../core/gateways/catalogContract";
import { useModules } from "../../core/profile/modulesContext";
import { formatMoney } from "../../shared/format";
import { AmountField, Button, ChoiceChips, type ChoiceOption } from "../../shared/ui";
import { CREDIT_CHOICE, type SaleDraft } from "./draft";
import type { SaleChecks } from "./saleChecks";
import { splitSum } from "./saleChecks";
import { FieldMessage } from "./FieldMessage";

export interface PaymentSectionProps {
  modes: readonly PaymentMode[];
  draft: SaleDraft;
  checks: SaleChecks;
  showErrors: boolean;
  update: (patch: Partial<SaleDraft>) => void;
}

/**
 * Mode de paiement en grosses pastilles, « À crédit » compris quand le module Créances est
 * actif (specs § 15.1) ; répartition facultative.
 */
export function PaymentSection({ modes, draft, checks, showErrors, update }: PaymentSectionProps) {
  const credit = useModules().has("receivables");
  const options: ChoiceOption<string>[] = [
    ...modes.map((mode) => ({ value: mode.id, label: mode.name })),
    ...(credit ? [{ value: CREDIT_CHOICE, label: "À crédit" }] : []),
  ];
  const cash = draft.payment !== null && draft.payment !== CREDIT_CHOICE;
  return (
    <section aria-label="Paiement" className="flex flex-col gap-4">
      <ChoiceChips
        label="Paiement"
        options={options}
        value={draft.payment}
        onChange={(payment) => {
          update({ payment, split: null });
        }}
      />
      {showErrors && checks.payment !== undefined && <FieldMessage text={checks.payment} />}
      {cash && draft.split === null && (
        <Button
          variant="ghost"
          icon={Split}
          fullWidth
          onClick={() => {
            const split = Object.fromEntries(modes.map((mode) => [mode.id, null]));
            update({ split: { ...split, [draft.payment ?? ""]: checks.total } });
          }}
        >
          Répartir sur plusieurs modes
        </Button>
      )}
      {cash && draft.split !== null && (
        <SplitPayments
          modes={modes}
          split={draft.split}
          total={checks.total}
          error={checks.split}
          showErrors={showErrors}
          update={update}
        />
      )}
    </section>
  );
}

function SplitPayments({
  modes,
  split,
  total,
  error,
  showErrors,
  update,
}: {
  modes: readonly PaymentMode[];
  split: Record<string, number | null>;
  total: number;
  error: string | undefined;
  showErrors: boolean;
  update: (patch: Partial<SaleDraft>) => void;
}) {
  const sum = splitSum(split);
  // Un dépassement est signalé tout de suite ; un manque, au moment de valider.
  const visibleError = error !== undefined && (showErrors || sum > total) ? error : undefined;
  return (
    <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
      <legend className="mb-2 p-0 text-label font-semibold text-text">
        Répartition du paiement
      </legend>
      {modes.map((mode) => (
        <AmountField
          key={mode.id}
          label={mode.name}
          value={split[mode.id] ?? null}
          onChange={(amount) => {
            update({ split: { ...split, [mode.id]: amount } });
          }}
        />
      ))}
      <p className="m-0 text-lead text-text">
        Total payé : <strong className="tabular-nums">{formatMoney(sum)}</strong> sur{" "}
        <span className="tabular-nums">{formatMoney(total)}</span>
      </p>
      {visibleError !== undefined && <FieldMessage text={visibleError} />}
      <Button
        variant="ghost"
        icon={Banknote}
        fullWidth
        onClick={() => {
          update({ split: null });
        }}
      >
        Payer avec un seul mode
      </Button>
    </fieldset>
  );
}
