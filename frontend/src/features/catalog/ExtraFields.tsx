import { TextField } from "../../shared/ui";
import { thresholdError, type ExtraDraft } from "./extraValues";

/** Champs facultatifs communs à tous les profils (UC-STK-01, étape 3). */
export function ExtraFields({
  draft,
  onChange,
}: {
  draft: ExtraDraft;
  onChange: (draft: ExtraDraft) => void;
}) {
  return (
    <>
      <TextField
        label="Seuil d'alerte"
        hint="Vide : le seuil de la boutique s'applique"
        inputMode="decimal"
        autoComplete="off"
        value={draft.threshold}
        error={thresholdError(draft.threshold)}
        onChange={(event) => {
          onChange({ ...draft, threshold: event.target.value });
        }}
      />
      <TextField
        label="Notes"
        autoComplete="off"
        value={draft.notes}
        onChange={(event) => {
          onChange({ ...draft, notes: event.target.value });
        }}
      />
    </>
  );
}
