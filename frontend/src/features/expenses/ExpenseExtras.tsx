import { Paperclip } from "lucide-react";
import { Button, ChoiceChips, TextField } from "../../shared/ui";
import { dateBounds } from "./businessDay";
import type { Draft, DraftProblems } from "./draft";
import type { References } from "./references";
import { TagPicker } from "./TagPicker";

/** Raison du justificatif indisponible (module des pièces jointes non livré). */
export const ATTACHMENTS_PENDING = "Pièces jointes : à venir";
/** Choix « aucun lieu » (le lieu est facultatif). */
export const NO_LOCATION = "aucun";

export interface ExpenseExtrasProps {
  shopId: string;
  refs: References;
  draft: Draft;
  problems: DraftProblems;
  showErrors: boolean;
  today: string;
  update: (patch: Partial<Draft>) => void;
  /** La description est affichée au-dessus quand la catégorie l'exige. */
  descriptionAbove: boolean;
}

/** Champs facultatifs sous « Plus de détails » (UC-DEP-01 étape 3). */
export function ExpenseExtras(props: ExpenseExtrasProps) {
  const { shopId, refs, draft, problems, showErrors, today, update, descriptionAbove } = props;
  const bounds = dateBounds(today, refs.me.role === "owner");
  const modes = refs.modes.filter((mode) => mode.active || mode.id === draft.modeId);
  const places = refs.locations.filter((l) => l.active || l.id === draft.locationId);
  return (
    <>
      <TagPicker
        shopId={shopId}
        value={draft.tags}
        onChange={(tags) => {
          update({ tags });
        }}
      />
      {!descriptionAbove && (
        <TextField
          label="Description"
          value={draft.description}
          maxLength={500}
          onChange={(event) => {
            update({ description: event.target.value });
          }}
        />
      )}
      {places.length > 0 && (
        <ChoiceChips
          label="Lieu"
          options={[
            { value: NO_LOCATION, label: "Aucun lieu" },
            ...places.map((place) => ({ value: place.id, label: place.name })),
          ]}
          value={draft.locationId ?? NO_LOCATION}
          onChange={(value) => {
            update({ locationId: value === NO_LOCATION ? null : value });
          }}
        />
      )}
      <TextField
        label="Bénéficiaire"
        hint="Ex. nom de l'employé payé"
        value={draft.beneficiary}
        maxLength={120}
        onChange={(event) => {
          update({ beneficiary: event.target.value });
        }}
      />
      {modes.length > 0 && (
        <ChoiceChips
          label="Mode de paiement"
          options={modes.map((mode) => ({ value: mode.id, label: mode.name }))}
          value={draft.modeId}
          onChange={(modeId) => {
            update({ modeId });
          }}
        />
      )}
      <TextField
        label="Date"
        type="date"
        value={draft.date}
        max={bounds.max}
        {...(bounds.min === undefined ? {} : { min: bounds.min })}
        error={showErrors ? problems.date : undefined}
        onChange={(event) => {
          update({ date: event.target.value });
        }}
      />
      <Button variant="secondary" icon={Paperclip} fullWidth disabledReason={ATTACHMENTS_PENDING}>
        Ajouter le justificatif
      </Button>
    </>
  );
}
