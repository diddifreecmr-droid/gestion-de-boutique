import { useState } from "react";
import { Ban, Check, Hash, Pencil, RotateCcw } from "lucide-react";
import type { PaymentModePatch, ShopPaymentMode } from "../../../core/gateways/shopAdminContract";
import { Badge, Button, TextField } from "../../../shared/ui";

export interface PaymentModeRowProps {
  mode: ShopPaymentMode;
  busy: boolean;
  onPatch: (patch: Omit<PaymentModePatch, "version">) => Promise<boolean>;
}

/** Un mode de paiement : renommer, demander ou non la référence, désactiver ou réactiver. */
export function PaymentModeRow({ mode, busy, onPatch }: PaymentModeRowProps) {
  const [name, setName] = useState<string | null>(null);
  const [error, setError] = useState<string | undefined>(undefined);

  const rename = async () => {
    if (name === null) return;
    if (name.trim() === "") {
      setError("Le nom est vide");
      return;
    }
    if (await onPatch({ name: name.trim() })) setName(null);
  };

  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <span className="flex flex-wrap items-center gap-2">
        <span className={`text-lead ${mode.active ? "text-text" : "text-text-muted"}`}>
          {mode.name}
        </span>
        {mode.reference_required && <Badge status="warning">Référence demandée</Badge>}
        {!mode.active && <Badge status="danger">Désactivé</Badge>}
      </span>
      {name !== null ? (
        <div className="flex flex-col gap-2">
          <TextField
            label={`Nouveau nom pour ${mode.name}`}
            value={name}
            maxLength={200}
            error={error}
            onChange={(event) => {
              setName(event.target.value);
              setError(undefined);
            }}
          />
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="secondary"
              fullWidth
              onClick={() => {
                setName(null);
              }}
            >
              Retour
            </Button>
            <Button
              variant="secondary"
              icon={Check}
              fullWidth
              loading={busy}
              onClick={() => void rename()}
            >
              Enregistrer
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            icon={Pencil}
            onClick={() => {
              setName(mode.name);
            }}
          >
            Renommer
          </Button>
          <Button
            variant="secondary"
            icon={Hash}
            loading={busy}
            onClick={() => void onPatch({ reference_required: !mode.reference_required })}
          >
            {mode.reference_required ? "Ne plus demander la référence" : "Demander la référence"}
          </Button>
          {mode.active ? (
            <Button
              variant="secondary"
              icon={Ban}
              loading={busy}
              onClick={() => void onPatch({ active: false })}
            >
              Désactiver
            </Button>
          ) : (
            <Button
              variant="secondary"
              icon={RotateCcw}
              loading={busy}
              onClick={() => void onPatch({ active: true })}
            >
              Réactiver
            </Button>
          )}
        </div>
      )}
    </li>
  );
}
