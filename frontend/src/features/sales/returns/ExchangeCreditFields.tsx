import { useModules } from "../../../core/profile/modulesContext";
import { AmountField, ChoiceChips, SummaryCard } from "../../../shared/ui";
import { FieldMessage } from "../FieldMessage";
import type { ExchangeKind, ReturnChecks, ReturnDraft } from "./returnDraft";

export interface ExchangeCreditFieldsProps {
  draft: ReturnDraft;
  checks: ReturnChecks;
  showErrors: boolean;
  update: (patch: Partial<ReturnDraft>) => void;
}

const KINDS: { value: ExchangeKind; label: string }[] = [
  { value: "cash", label: "Comptant" },
  { value: "credit", label: "À crédit" },
];

/**
 * Nouvelle vente de l'échange au comptant ou **à crédit** (décision client specs § 15.1) :
 * à crédit, le client est celui de la vente d'origine (imposé), un acompte facultatif est
 * versé dans le mode de l'échange, le reste devient une créance. Sans le module Créances, le
 * choix n'est pas proposé : l'échange est au comptant.
 */
export function ExchangeCreditFields({
  draft,
  checks,
  showErrors,
  update,
}: ExchangeCreditFieldsProps) {
  const credit = draft.exchangeKind === "credit";
  if (!useModules().has("receivables")) return null;
  return (
    <>
      <ChoiceChips
        label="Paiement de la nouvelle vente"
        options={KINDS}
        value={draft.exchangeKind}
        onChange={(exchangeKind) => {
          update({ exchangeKind });
        }}
      />
      {credit && (
        <>
          <p className="m-0 text-body text-text-muted">
            Client : celui de la vente d'origine (il ne se change pas).
          </p>
          {showErrors && checks.credit !== undefined && <FieldMessage text={checks.credit} />}
          <AmountField
            label="Acompte versé aujourd'hui"
            hint="Laissez vide ou 0 si rien n'est versé"
            value={draft.deposit}
            error={showErrors ? checks.deposit : undefined}
            onChange={(deposit) => {
              update({ deposit });
            }}
          />
          <SummaryCard
            lines={[
              { label: "À payer en plus de l'avoir", amount: checks.balance.toPay },
              { label: "Versé", amount: Math.min(draft.deposit ?? 0, checks.balance.toPay) },
            ]}
            due={checks.creditDue}
          />
        </>
      )}
    </>
  );
}
