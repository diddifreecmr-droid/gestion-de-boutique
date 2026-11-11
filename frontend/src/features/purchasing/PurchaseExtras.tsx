import { Camera } from "lucide-react";
import { Button, TextField } from "../../shared/ui";
import type { DraftProblems, FeeDraft, PurchaseDraft } from "./draft";
import { FeesEditor } from "./FeesEditor";

/** Raison affichée sous le bouton photo tant que les pièces jointes n'existent pas. */
export const ATTACHMENTS_PENDING = "Pièces jointes : à venir";

export interface PurchaseExtrasProps {
  draft: PurchaseDraft;
  problems: DraftProblems;
  showErrors: boolean;
  update: (patch: Partial<PurchaseDraft>) => void;
}

/** « Plus de détails » de l'achat (UC-ACH-01 étape 4) : frais, facture, photo, note. */
export function PurchaseExtras({ draft, problems, showErrors, update }: PurchaseExtrasProps) {
  return (
    <>
      <FeesEditor
        fees={draft.fees}
        problems={problems.fees}
        showErrors={showErrors}
        onChange={(fees: FeeDraft[]) => {
          update({ fees });
        }}
      />
      <TextField
        label="Numéro de facture du fournisseur"
        maxLength={64}
        autoComplete="off"
        value={draft.invoiceRef}
        onChange={(event) => {
          update({ invoiceRef: event.target.value });
        }}
      />
      <Button variant="secondary" icon={Camera} disabledReason={ATTACHMENTS_PENDING}>
        Photo de la facture
      </Button>
      <TextField
        label="Note"
        maxLength={500}
        value={draft.note}
        onChange={(event) => {
          update({ note: event.target.value });
        }}
      />
    </>
  );
}
