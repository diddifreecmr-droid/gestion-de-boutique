import { useState, type ReactNode } from "react";
import { Plus } from "lucide-react";
import type { Role } from "../../core/auth/me";
import type { PaymentMode, SaleLocation } from "../../core/gateways/catalogContract";
import type { SaleResult } from "../../core/gateways/salesContract";
import { Button } from "../../shared/ui";
import { FormAlert } from "../auth/FormAlert";
import { ArticlePicker } from "./ArticlePicker";
import { CreditSection } from "./CreditSection";
import { CREDIT_CHOICE, newDraft, newLine, type SaleDraft } from "./draft";
import { readLastPaymentMode } from "./lastPaymentMode";
import { PaymentSection } from "./PaymentSection";
import { SaleActionBar } from "./SaleActionBar";
import { checkSale } from "./saleChecks";
import { SaleExtras } from "./SaleExtras";
import { SaleLineCard } from "./SaleLineCard";
import { useSaleSubmit } from "./useSaleSubmit";

export interface NewSaleFormProps {
  shopId: string;
  role: Role;
  location: SaleLocation;
  modes: readonly PaymentMode[];
  onRecorded: (sale: SaleResult) => void;
  /** Mention sous le titre (ex. « Démonstration » tant que la passerelle est simulée). */
  notice?: ReactNode;
}

/** Le dernier mode utilisé s'il existe encore, sinon le premier (jamais « À crédit »). */
function initialPayment(shopId: string, modes: readonly PaymentMode[]): string {
  const [first] = modes;
  if (first === undefined) throw new Error("La boutique n'a aucun mode de paiement actif");
  const last = readLastPaymentMode(shopId);
  return modes.some((mode) => mode.id === last) && last !== null ? last : first.id;
}

/** Formulaire « Nouvelle vente » (design-system § 7.1) : article, prix, paiement, valider. */
export function NewSaleForm(props: NewSaleFormProps) {
  const { shopId, role, location, modes, onRecorded, notice } = props;
  const [draft, setDraft] = useState<SaleDraft>(() => newDraft(initialPayment(shopId, modes)));
  const [picking, setPicking] = useState(false);
  const update = (patch: Partial<SaleDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const checks = checkSale(draft, role);
  const submit = useSaleSubmit({ shopId, location, draft, checks, update, onRecorded });
  const showPicker = picking || draft.lines.length === 0;

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Nouvelle vente</h1>
      {notice}
      {draft.lines.map((line) => (
        <SaleLineCard
          key={line.key}
          line={line}
          locationName={location.name}
          issues={checks.lines[line.key]}
          showErrors={submit.showErrors}
          onChange={(next) => {
            update({ lines: draft.lines.map((l) => (l.key === line.key ? next : l)) });
          }}
          {...(draft.lines.length > 1
            ? {
                onRemove: () => {
                  update({ lines: draft.lines.filter((l) => l.key !== line.key) });
                },
              }
            : {})}
        />
      ))}
      {showPicker ? (
        <ArticlePicker
          shopId={shopId}
          locationId={location.id}
          locationName={location.name}
          excluded={draft.lines.map((line) => line.article.id)}
          onPick={(article) => {
            update({ lines: [...draft.lines, newLine(article)] });
            setPicking(false);
          }}
          {...(draft.lines.length > 0
            ? {
                onClose: () => {
                  setPicking(false);
                },
              }
            : {})}
        />
      ) : (
        <Button
          variant="secondary"
          icon={Plus}
          fullWidth
          onClick={() => {
            setPicking(true);
          }}
        >
          Ajouter un article
        </Button>
      )}
      <PaymentSection
        modes={modes}
        draft={draft}
        checks={checks}
        showErrors={submit.showErrors}
        update={update}
      />
      {draft.payment === CREDIT_CHOICE && (
        <CreditSection
          shopId={shopId}
          modes={modes}
          draft={draft}
          checks={checks}
          showErrors={submit.showErrors}
          update={update}
        />
      )}
      <SaleExtras
        shopId={shopId}
        draft={draft}
        checks={checks}
        showErrors={submit.showErrors}
        update={update}
      />
      <FormAlert message={submit.message} />
      <SaleActionBar
        total={checks.total}
        needsApproval={checks.needsApproval.length > 0}
        approval={submit.approval}
        submitting={submit.submitting}
        onSubmit={() => void submit.submit()}
        onRequestApproval={() => void submit.requestApproval()}
      />
    </>
  );
}
