import { CirclePlus, Trash2 } from "lucide-react";
import type { FeeKind } from "../../core/gateways/purchasingContract";
import { AmountField, Button, TextField } from "../../shared/ui";
import { emptyFee, type FeeDraft } from "./draft";
import { FEE_KINDS, FEE_LABELS } from "./fees";

export interface FeesEditorProps {
  fees: readonly FeeDraft[];
  problems: Readonly<Record<string, string>>;
  showErrors: boolean;
  onChange: (fees: FeeDraft[]) => void;
}

/** Bouton d'ajout : « Ajouter : Douane ». */
const addLabel = (kind: FeeKind) => `Ajouter : ${FEE_LABELS[kind]}`;

/**
 * Frais facultatifs (UC-ACH-01 étape 4) : Transport, Douane, Manutention, Autre (+ libellé).
 * Ils se répartissent sur les lignes au prorata de leur valeur (RG-T10, récapitulatif).
 */
export function FeesEditor({ fees, problems, showErrors, onChange }: FeesEditorProps) {
  const update = (key: string, patch: Partial<FeeDraft>) => {
    onChange(fees.map((fee) => (fee.key === key ? { ...fee, ...patch } : fee)));
  };
  return (
    <div className="flex flex-col gap-4">
      <p className="m-0 text-label font-semibold text-text">Frais d'achat</p>
      {fees.map((fee) => {
        const name = FEE_LABELS[fee.kind];
        const error = showErrors ? problems[fee.key] : undefined;
        return (
          <div key={fee.key} className="flex flex-col gap-2 rounded-lg border border-border p-4">
            {fee.kind === "other" && (
              <TextField
                label="Libellé des frais"
                maxLength={120}
                value={fee.label}
                error={error !== undefined && fee.amount !== null ? error : undefined}
                onChange={(event) => {
                  update(fee.key, { label: event.target.value });
                }}
              />
            )}
            <AmountField
              label={`Frais : ${name}`}
              value={fee.amount}
              error={fee.amount === null ? error : undefined}
              onChange={(amount) => {
                update(fee.key, { amount });
              }}
            />
            <Button
              variant="ghost"
              icon={Trash2}
              onClick={() => {
                onChange(fees.filter((item) => item.key !== fee.key));
              }}
            >
              {`Retirer les frais : ${name}`}
            </Button>
          </div>
        );
      })}
      <div className="grid grid-cols-2 gap-2">
        {FEE_KINDS.map((kind) => (
          <Button
            key={kind}
            variant="secondary"
            icon={CirclePlus}
            onClick={() => {
              onChange([...fees, emptyFee(kind)]);
            }}
          >
            {addLabel(kind)}
          </Button>
        ))}
      </div>
    </div>
  );
}
