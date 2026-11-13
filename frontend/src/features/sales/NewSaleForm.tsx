import { useState, type ReactNode } from "react";
import type { Role } from "../../core/auth/me";
import type { PaymentMode, SaleLocation, SaleShortcut } from "../../core/gateways/catalogContract";
import type { SaleResult } from "../../core/gateways/salesContract";
import { FormAlert } from "../auth/FormAlert";
import { CreditSection } from "./CreditSection";
import { CREDIT_CHOICE, newDraft, type SaleDraft } from "./draft";
import { UNIT_FIELDS, type LineFields } from "./lineFields";
import { defaultPayment } from "./paymentChoices";
import { PaymentSection } from "./PaymentSection";
import { SaleActionBar } from "./SaleActionBar";
import { SaleBasket } from "./SaleBasket";
import { checkSale } from "./saleChecks";
import { SaleExtras } from "./SaleExtras";
import { usePriceApproval } from "./priceRequests/usePriceApproval";
import { useSaleSubmit } from "./useSaleSubmit";

export interface NewSaleFormProps {
  shopId: string;
  role: Role;
  location: SaleLocation;
  modes: readonly PaymentMode[];
  /** Réglage « Accord du propriétaire sous le prix minimum » (`SaleSetup`). */
  requiresApproval: boolean;
  onRecorded: (sale: SaleResult) => void;
  /** Mention sous le titre (ex. « Démonstration » tant que la passerelle est simulée). */
  notice?: ReactNode;
  /** Aide de la recherche d'article, selon les champs du profil (`articleSearchHint`). */
  searchHint: string;
  /** Champs d'une ligne selon le profil (`lineFieldsOf`) ; Motos par défaut. */
  fields?: LineFields;
  /** Raccourcis de longueur du profil (Textile, `SaleSetup.sale_shortcuts`). */
  shortcuts?: readonly SaleShortcut[];
}

/**
 * Formulaire « Nouvelle vente » (design-system § 7.1, § 7.4) : lignes (panier), paiement,
 * valider. Aucune remise (QC-2) : le total est la somme des lignes, au prix négocié de chacune.
 */
export function NewSaleForm(props: NewSaleFormProps) {
  const { shopId, role, location, modes, requiresApproval, onRecorded, notice, searchHint } = props;
  const [draft, setDraft] = useState<SaleDraft>(() => newDraft(defaultPayment(modes)));
  const update = (patch: Partial<SaleDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const checks = checkSale(draft, role, requiresApproval || draft.approvalRequired);
  const approval = usePriceApproval(shopId, checks.needsApproval);
  const submit = useSaleSubmit({ shopId, location, draft, checks, approval, update, onRecorded });

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Nouvelle vente</h1>
      {notice}
      <SaleBasket
        shopId={shopId}
        location={location}
        lines={draft.lines}
        issues={checks.lines}
        showErrors={submit.showErrors}
        fields={props.fields ?? UNIT_FIELDS}
        searchHint={searchHint}
        shortcuts={props.shortcuts ?? []}
        onLines={(lines) => {
          update({ lines });
        }}
      />
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
      <FormAlert message={submit.message ?? approval.message} />
      <SaleActionBar
        total={checks.total}
        lineCount={draft.lines.length}
        approval={approval.view}
        submitting={submit.submitting}
        onSubmit={() => void submit.submit()}
        onRequestApproval={() => void approval.ask()}
        onRefreshApproval={() => void approval.refresh()}
      />
    </>
  );
}
