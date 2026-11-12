import type { ShopRole } from "../../../core/gateways/shopAdminContract";
import { salePoints, type MemberRefs } from "./memberRefs";

/** Rôle choisi et, pour un vendeur, son lieu de vente habituel. */
export interface RoleDraft {
  role: ShopRole;
  locationId: string | null;
}

export const NO_SALE_POINT =
  "Aucun point de vente actif : ajoutez-en un dans « Lieux » avant d'ajouter un vendeur.";

/** Erreur de saisie du lieu, ou null si le choix est complet. */
export function roleDraftError(refs: MemberRefs, draft: RoleDraft): string | null {
  if (draft.role !== "seller") return null;
  const points = salePoints(refs);
  if (points.length === 0) return NO_SALE_POINT;
  const chosen = points.some((point) => point.id === draft.locationId);
  return chosen ? null : "Choisissez le lieu de vente habituel";
}
