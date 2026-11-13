import { useState } from "react";
import { Banknote, Ellipsis, Split } from "lucide-react";
import type { PaymentMode } from "../../core/gateways/catalogContract";
import { useModules } from "../../core/profile/modulesContext";
import { formatMoney } from "../../shared/format";
import { AmountField, Button, ChoiceChips, type ChoiceOption } from "../../shared/ui";
import { CREDIT_CHOICE, type SaleDraft } from "./draft";
import type { SaleChecks } from "./saleChecks";
import { splitSum } from "./saleChecks";
import { FieldMessage } from "./FieldMessage";
import { groupModes } from "./paymentChoices";

export interface PaymentSectionProps {
  modes: readonly PaymentMode[];
  draft: SaleDraft;
  checks: SaleChecks;
  showErrors: boolean;
  update: (patch: Partial<SaleDraft>) => void;
}

const toOption = (mode: PaymentMode): ChoiceOption<string> => ({
  value: mode.id,
  label: mode.name,
});

/**
 * Mode de paiement en grosses pastilles : « Espèces » et les 2 premiers autres modes, puis
 * « À crédit » quand le module Créances est actif (specs § 15.1) ; les autres modes et la
 * répartition sont derrière « Autre mode » (audit UX du 13/11/2026). Un mode choisi parmi
 * les autres reste affiché quand on referme.
 */
export function PaymentSection({ modes, draft, checks, showErrors, update }: PaymentSectionProps) {
  const credit = useModules().has("receivables");
  const { visible, hidden } = groupModes(modes);
  const [more, setMore] = useState(false);
  const options: ChoiceOption<string>[] = [
    ...visible.map(toOption),
    ...(credit ? [{ value: CREDIT_CHOICE, label: "À crédit" }] : []),
    ...hidden.filter((mode) => more || mode.id === draft.payment).map(toOption),
  ];
  const cash = draft.payment !== null && draft.payment !== CREDIT_CHOICE;
  const extended = more || hidden.length === 0;
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
      {hidden.length > 0 && (
        <Button
          variant="ghost"
          icon={Ellipsis}
          fullWidth
          aria-expanded={more}
          onClick={() => {
            setMore((open) => !open);
          }}
        >
          Autre mode
        </Button>
      )}
      {extended && cash && draft.split === null && (
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
