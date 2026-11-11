/**
 * Section « Ventes » (propriétaire) / « Mes ventes » (vendeur), UC-VEN-05 : la fiche est
 * dans l'adresse (`?id=`), si bien que le bouton retour du téléphone revient à la liste.
 */
import type { Role } from "../../core/auth/me";

/** Segment d'URL de l'écran « Nouvelle vente » (clé du menu vendeur, CDC § 17.4). */
export const NEW_SALE_KEY = "nouvelle-vente";
/** Entrée « Ventes » du propriétaire. */
export const SALES_KEY = "ventes";
/** Entrée « Mes ventes » du vendeur. */
export const MY_SALES_KEY = "mes-ventes";

export type SaleRole = "owner" | "seller";

/** Rôle admis à la section ; tout autre rôle est une erreur de garde (fail-fast). */
export function saleRole(role: Role): SaleRole {
  if (role === "owner" || role === "seller") return role;
  throw new Error(`Le rôle « ${role} » ne consulte pas les ventes (garde de route manquante)`);
}

/** Adresse relative de la fiche d'une vente. */
export function saleLink(id: string): string {
  return `?id=${encodeURIComponent(id)}`;
}
