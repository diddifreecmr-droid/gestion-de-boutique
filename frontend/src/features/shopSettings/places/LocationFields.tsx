import { ChoiceChips, TextField } from "../../../shared/ui";
import { YesNoChips } from "../YesNoChips";
import { KIND_OPTIONS, type LocationDraft } from "./locationDraft";

export interface LocationFieldsProps {
  /** Préfixe des libellés, pour distinguer plusieurs formulaires à l'écran. */
  prefix: string;
  draft: LocationDraft;
  nameError: string | undefined;
  onChange: (draft: LocationDraft) => void;
}

/** Champs d'un lieu (UC-SOC-05) : nom unique, type, point de vente, ville. */
export function LocationFields({ prefix, draft, nameError, onChange }: LocationFieldsProps) {
  return (
    <>
      <TextField
        label={`${prefix} — nom`}
        value={draft.name}
        maxLength={200}
        error={nameError}
        onChange={(event) => {
          onChange({ ...draft, name: event.target.value });
        }}
      />
      <ChoiceChips
        label={`${prefix} — type`}
        options={KIND_OPTIONS}
        value={draft.kind}
        onChange={(kind) => {
          onChange({ ...draft, kind });
        }}
      />
      <YesNoChips
        label={`${prefix} — point de vente`}
        value={draft.isPointOfSale}
        onChange={(isPointOfSale) => {
          onChange({ ...draft, isPointOfSale });
        }}
      />
      <TextField
        label={`${prefix} — ville (facultatif)`}
        value={draft.city}
        maxLength={200}
        onChange={(event) => {
          onChange({ ...draft, city: event.target.value });
        }}
      />
    </>
  );
}
