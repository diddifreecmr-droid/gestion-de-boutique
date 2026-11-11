import type { Supplier } from "../../core/gateways/purchasingContract";
import { ChoiceChips, TextField } from "../../shared/ui";
import { dateBounds } from "../expenses/businessDay";
import { DEFAULT_LOCATION, type PurchaseDraft } from "./draft";
import type { References } from "./references";
import { SupplierPicker } from "./SupplierPicker";

/** Choix « lieu réglé par défaut » (le comptable ne lit pas les réglages : le serveur l'applique). */
export const DEFAULT_LOCATION_LABEL = "Lieu de réception habituel";

export interface PurchaseHeaderProps {
  shopId: string;
  refs: References;
  draft: PurchaseDraft;
  today: string;
  dateError: string | undefined;
  update: (patch: Partial<PurchaseDraft>) => void;
  onSupplierSaved: (supplier: Supplier) => void;
  /** Correction : le lieu enregistré reste proposé même désactivé, sans « lieu habituel ». */
  keepLocationId?: string | undefined;
}

/** Lieux proposés : actifs (+ celui de l'achat corrigé), précédés du lieu habituel si besoin. */
function locationOptions(refs: References, keep: string | undefined) {
  const places = refs.locations
    .filter((place) => place.active || place.id === keep)
    .map((place) => ({ value: place.id, label: place.name }));
  const withDefault = keep === undefined && refs.me.role === "accountant";
  return withDefault
    ? [{ value: DEFAULT_LOCATION, label: DEFAULT_LOCATION_LABEL }, ...places]
    : places;
}

/** En-tête de l'achat (UC-ACH-01 étape 2) : fournisseur facultatif, date, lieu de réception. */
export function PurchaseHeader(props: PurchaseHeaderProps) {
  const { refs, draft, today, update } = props;
  const bounds = dateBounds(today, refs.me.role === "owner");
  const options = locationOptions(refs, props.keepLocationId);
  if (options.length === 0) throw new Error("Aucun lieu de réception actif");
  return (
    <>
      <SupplierPicker
        shopId={props.shopId}
        suppliers={refs.suppliers}
        value={draft.supplier}
        onChange={(supplier) => {
          update({ supplier });
        }}
        onCreated={props.onSupplierSaved}
      />
      <TextField
        label="Date de l'achat"
        type="date"
        value={draft.date}
        max={bounds.max}
        {...(bounds.min === undefined ? {} : { min: bounds.min })}
        error={props.dateError}
        onChange={(event) => {
          update({ date: event.target.value });
        }}
      />
      <ChoiceChips
        label="Lieu de réception"
        options={options}
        value={draft.locationId}
        onChange={(locationId) => {
          update({ locationId });
        }}
      />
    </>
  );
}
