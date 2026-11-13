import { AmountField } from "../../shared/ui";
import type { CreatePrices } from "./createPrices";
import type { PriceLabels } from "./textileFields";

export interface CreatePriceFieldsProps {
  labels: PriceLabels;
  /** Réglage « prix minimum » de la boutique (H9). */
  minPriceEnabled: boolean;
  value: CreatePrices;
  onChange: (value: CreatePrices) => void;
}

/** « Prix de base » (ou « Prix au mètre » et « Prix à la pièce » en Textile) et minimums. */
export function CreatePriceFields({
  labels,
  minPriceEnabled,
  value,
  onChange,
}: CreatePriceFieldsProps) {
  const set = (patch: Partial<CreatePrices>) => {
    onChange({ ...value, ...patch });
  };
  return (
    <>
      <AmountField
        label={`${labels.base} (facultatif)`}
        hint="Vide : le prix sera tapé à chaque vente"
        value={value.base}
        onChange={(base) => {
          set({ base });
        }}
      />
      {minPriceEnabled && (
        <AmountField
          label={
            labels.piece === null ? "Prix minimum (facultatif)" : "Minimum au mètre (facultatif)"
          }
          value={value.minimum}
          onChange={(minimum) => {
            set({ minimum });
          }}
        />
      )}
      {labels.piece !== null && (
        <AmountField
          label={`${labels.piece} (facultatif)`}
          value={value.piece}
          onChange={(piece) => {
            set({ piece });
          }}
        />
      )}
      {labels.piece !== null && minPriceEnabled && (
        <AmountField
          label="Minimum à la pièce (facultatif)"
          value={value.minimumPiece}
          onChange={(minimumPiece) => {
            set({ minimumPiece });
          }}
        />
      )}
    </>
  );
}
