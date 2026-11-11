/**
 * Référentiels des écrans Achats : fournisseurs (inactifs compris, pour nommer les anciens
 * achats), lieux, modes de paiement et — pour le propriétaire, seul à lire les réglages — le
 * lieu de réception par défaut. Une référence inconnue est une incohérence de données : on lève
 * plutôt que d'afficher un identifiant.
 */
import type {
  PurchaseLocation,
  PurchasePaymentMode,
  PurchasingGateway,
  Supplier,
} from "../../core/gateways/purchasingContract";
import { DEFAULT_LOCATION } from "./draft";
import type { PurchaseRole } from "./purchasingNav";

export interface References {
  suppliers: readonly Supplier[];
  locations: readonly PurchaseLocation[];
  modes: readonly PurchasePaymentMode[];
  /** Lieu de réception réglé (propriétaire) ; `null` : inconnu de l'écran ou non réglé. */
  reception: string | null;
  me: { userId: string; role: PurchaseRole };
}

const byOrder = <T extends { display_order: number }>(items: readonly T[]): T[] =>
  [...items].sort((a, b) => a.display_order - b.display_order);

export async function loadReferences(
  gateway: PurchasingGateway,
  shopId: string,
  me: References["me"],
): Promise<References> {
  const [suppliers, locations, modes, reception] = await Promise.all([
    gateway.suppliers(shopId),
    gateway.locations(shopId),
    gateway.paymentModes(shopId),
    me.role === "owner" ? gateway.receptionLocation(shopId) : Promise.resolve(null),
  ]);
  return {
    suppliers: [...suppliers].sort((a, b) => a.name.localeCompare(b.name, "fr")),
    locations: byOrder(locations),
    modes: byOrder(modes),
    reception,
    me,
  };
}

function named(items: readonly { id: string; name: string }[], id: string, kind: string): string {
  const found = items.find((item) => item.id === id);
  if (found === undefined) throw new Error(`${kind} inconnu : « ${id} »`);
  return found.name;
}

export const locationName = (refs: References, id: string) => named(refs.locations, id, "Lieu");
export const modeName = (refs: References, id: string) => named(refs.modes, id, "Mode de paiement");

/** Nom du fournisseur, ou « Sans fournisseur » (il est facultatif, UC-ACH-01). */
export function supplierName(refs: References, id: string | null): string {
  return id === null ? "Sans fournisseur" : named(refs.suppliers, id, "Fournisseur");
}

/** Références avec un fournisseur ajouté ou modifié (création rapide, fiche). */
export function withSupplier(refs: References, supplier: Supplier): References {
  const others = refs.suppliers.filter((item) => item.id !== supplier.id);
  const suppliers = [...others, supplier].sort((a, b) => a.name.localeCompare(b.name, "fr"));
  return { ...refs, suppliers };
}

/**
 * Lieu présélectionné (CDC § 1.3 « pré-remplir ») : le lieu de réception réglé (propriétaire),
 * sinon le premier lieu actif ; le comptable ne lit pas les réglages et laisse le serveur
 * appliquer le lieu habituel (Q-01 : Garoua-Boulaï pour les motos).
 */
export function initialLocation(refs: References): string {
  if (refs.me.role === "accountant") return DEFAULT_LOCATION;
  const reception = refs.locations.find((place) => place.id === refs.reception && place.active);
  const first = reception ?? refs.locations.find((place) => place.active);
  if (first === undefined) throw new Error("Aucun lieu actif pour recevoir un achat");
  return first.id;
}
