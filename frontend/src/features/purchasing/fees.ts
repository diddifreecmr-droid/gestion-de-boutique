/** Frais d'un achat (CDC UC-ACH-01 étape 4, backend `FeeKind`) : libellés à l'écran. */
import type { FeeKind } from "../../core/gateways/purchasingContract";

export const FEE_LABELS: Readonly<Record<FeeKind, string>> = {
  transport: "Transport",
  customs: "Douane",
  handling: "Manutention",
  other: "Autre",
};

export const FEE_KINDS: readonly FeeKind[] = ["transport", "customs", "handling", "other"];

export function feeKind(value: string): FeeKind {
  const found = FEE_KINDS.find((kind) => kind === value);
  if (found === undefined) throw new Error(`Type de frais inconnu : « ${value} »`);
  return found;
}

/** « Douane », ou le libellé saisi pour « Autre » (« Autre — Gardiennage »). */
export function feeText(kind: string, label: string | null): string {
  const name = FEE_LABELS[feeKind(kind)];
  return label === null || label === "" ? name : `${name} — ${label}`;
}
