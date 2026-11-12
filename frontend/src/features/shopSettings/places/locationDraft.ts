import type { LocationKind } from "../../../core/gateways/shopAdminContract";

/** Saisie d'un lieu (création ou modification). */
export interface LocationDraft {
  name: string;
  kind: LocationKind;
  isPointOfSale: boolean;
  city: string;
}

export const KIND_LABELS: Readonly<Record<LocationKind, string>> = {
  store: "Boutique",
  warehouse: "Entrepôt",
};

export const KIND_OPTIONS: readonly { value: LocationKind; label: string }[] = [
  { value: "store", label: KIND_LABELS.store },
  { value: "warehouse", label: KIND_LABELS.warehouse },
];

export const EMPTY_LOCATION: LocationDraft = {
  name: "",
  kind: "store",
  isPointOfSale: true,
  city: "",
};
