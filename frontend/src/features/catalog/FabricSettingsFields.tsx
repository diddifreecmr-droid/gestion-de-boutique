import type { PieceWords } from "../../core/profile/pieceWords";
import { Switch, TextField } from "../../shared/ui";
import { CreatePriceFields } from "./CreatePriceFields";
import type { FabricErrors, FabricSettings } from "./fabricDraft";

export interface FabricSettingsFieldsProps {
  value: FabricSettings;
  onChange: (value: FabricSettings) => void;
  errors: FabricErrors;
  words: PieceWords;
  /** Le rôle fixe les prix (propriétaire) ; le comptable ne les voit pas. */
  setPrices: boolean;
  minPriceEnabled: boolean;
}

/**
 * Réglages partagés par toutes les couleurs d'un tissu : prix au mètre et au rouleau, minimums,
 * longueur du rouleau, « Au mètre seulement » (le rouleau disparaît), seuil d'alerte.
 */
export function FabricSettingsFields(props: FabricSettingsFieldsProps) {
  const { value, onChange, errors, words } = props;
  const set = (patch: Partial<FabricSettings>) => {
    onChange({ ...value, ...patch });
  };
  const perPiece = `Prix ${words.per}`;
  return (
    <>
      <Switch
        label="Au mètre seulement"
        hint={`Ce tissu ne se vend pas ${words.per}`}
        checked={value.meterOnly}
        onChange={(meterOnly) => {
          set({ meterOnly });
        }}
      />
      {!value.meterOnly && (
        <TextField
          label={`Longueur ${words.of}`}
          inputMode="decimal"
          autoComplete="off"
          suffix="m"
          hint="Par exemple 30 ou 25,5"
          value={value.rollLength}
          error={errors.rollLength}
          onChange={(event) => {
            set({ rollLength: event.target.value });
          }}
        />
      )}
      {props.setPrices && (
        <CreatePriceFields
          labels={{
            base: "Prix au mètre",
            piece: value.meterOnly ? null : perPiece,
            pieceMinimum: value.meterOnly ? null : `Minimum ${words.per}`,
          }}
          minPriceEnabled={props.minPriceEnabled}
          value={value.prices}
          onChange={(prices) => {
            set({ prices });
          }}
        />
      )}
      <TextField
        label="Seuil d'alerte (facultatif)"
        inputMode="decimal"
        autoComplete="off"
        suffix="m"
        hint="Vide : le seuil de la boutique"
        value={value.threshold}
        error={errors.threshold}
        onChange={(event) => {
          set({ threshold: event.target.value });
        }}
      />
    </>
  );
}
