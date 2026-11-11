import { useState } from "react";
import { Check } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { InstallmentResult, Receivable } from "../../core/gateways/receivablesContract";
import { formatMoney } from "../../shared/format";
import { ActionBar, AmountField, Button, ChoiceChips, TextField } from "../../shared/ui";
import { businessDate, dateBounds } from "../expenses/businessDay";
import { FormMessage } from "../expenses/FormMessage";
import {
  emptyInstallment,
  installmentBody,
  installmentProblems,
  remainingAfter,
  type InstallmentDraft,
} from "./installmentDraft";
import { activeModes, type References } from "./references";
import { useAction } from "./useAction";

export interface InstallmentFormProps {
  shopId: string;
  refs: References;
  receivable: Receivable;
  onRecorded: (result: InstallmentResult) => void;
}

/**
 * Montant, mode, date, référence (UC-CRE-03 étape 2) ; « Reste à payer après ce versement »
 * affiché avant validation (étape 3). Un identifiant par saisie : renvoyer ne double rien.
 */
export function InstallmentForm({ shopId, refs, receivable, onRecorded }: InstallmentFormProps) {
  const { gateway, now } = useReceivablesDeps();
  const today = businessDate(now());
  const modes = activeModes(refs);
  const isOwner = refs.me.role === "owner";
  const [draft, setDraft] = useState<InstallmentDraft>(() => emptyInstallment(modes, today));
  const [showErrors, setShowErrors] = useState(false);
  const [clientId] = useState(uuidV7);
  const action = useAction();
  const update = (patch: Partial<InstallmentDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const context = { remaining: receivable.remaining, modes, today, isOwner };
  const problems = installmentProblems(draft, context);
  const shown = showErrors ? problems : {};
  const after = remainingAfter(receivable.remaining, draft.amount);
  const bounds = dateBounds(today, isOwner);

  const submit = async () => {
    setShowErrors(true);
    if (Object.keys(problems).length > 0) return;
    await action.run(async () => {
      onRecorded(await gateway.pay(shopId, receivable.id, installmentBody(draft, clientId), now()));
    });
  };

  return (
    <>
      <AmountField
        label="Montant du versement"
        value={draft.amount}
        error={shown.amount ?? (draft.amount !== null ? problems.amount : undefined)}
        onChange={(amount) => {
          update({ amount });
        }}
      />
      {modes.length === 0 ? (
        <FormMessage text="Aucun mode de paiement actif : le propriétaire doit en activer un." />
      ) : (
        <ChoiceChips
          label="Mode de paiement"
          options={modes.map((mode) => ({ value: mode.id, label: mode.name }))}
          value={draft.modeId}
          onChange={(modeId) => {
            update({ modeId });
          }}
        />
      )}
      {shown.mode !== undefined && <FormMessage text={shown.mode} />}
      <TextField
        label="Date du versement"
        type="date"
        max={bounds.max}
        {...(bounds.min === undefined ? {} : { min: bounds.min })}
        value={draft.paidOn}
        error={shown.date}
        onChange={(event) => {
          update({ paidOn: event.target.value });
        }}
      />
      <TextField
        label="Référence (facultatif)"
        hint="N° de transaction Mobile Money, de chèque…"
        maxLength={64}
        value={draft.reference}
        error={shown.reference}
        onChange={(event) => {
          update({ reference: event.target.value });
        }}
      />
      {action.message !== null && <FormMessage text={action.message} />}
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar
          fixed={false}
          summary={
            <span className="text-credit-text">
              Reste à payer après ce versement :{" "}
              <strong className="tabular-nums">{formatMoney(after ?? receivable.remaining)}</strong>
            </span>
          }
        >
          <Button
            size="lg"
            fullWidth
            icon={Check}
            loading={action.busy}
            onClick={() => void submit()}
          >
            Valider le versement
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
