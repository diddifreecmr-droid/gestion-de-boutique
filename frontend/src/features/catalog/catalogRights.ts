/**
 * Ce que chaque rôle fait du catalogue (CDC § 4.2, UC-STK-01 à 04 ; backend `role_matrix.py`).
 * Le serveur reste juge : ces droits ne servent qu'à ne pas montrer une action interdite
 * (CDC § 1.3). Le vendeur consulte le stock (module Stock) mais ne gère pas le catalogue ;
 * le chauffeur n'y a aucun accès.
 */
import type { Role } from "../../core/auth/me";

/** Rôles qui ouvrent les écrans du catalogue (section « Stock »). */
export const CATALOG_ROLES: readonly Role[] = ["owner", "accountant"];

/** Section du menu qui héberge le catalogue (CDC § 17.4 : « Stock »). */
export const STOCK_KEY = "stock";

export interface CatalogRights {
  /** Créer et modifier un article (UC-STK-01, 02). */
  edit: boolean;
  /** Fixer le prix de base et le prix minimum (UC-STK-03). */
  setPrices: boolean;
  /** Archiver ou réactiver (UC-STK-04). */
  archive: boolean;
}

const RIGHTS: Readonly<Record<"owner" | "accountant", CatalogRights>> = {
  owner: { edit: true, setPrices: true, archive: true },
  accountant: { edit: true, setPrices: false, archive: false },
};

export type CatalogRole = keyof typeof RIGHTS;

/** Rôle admis aux écrans du catalogue ; tout autre rôle est une erreur de garde (fail-fast). */
export function catalogRole(role: Role): CatalogRole {
  if (role === "owner" || role === "accountant") return role;
  throw new Error(`Le rôle « ${role} » n'a pas accès à la gestion du catalogue`);
}

export function catalogRights(role: CatalogRole): CatalogRights {
  return RIGHTS[role];
}
