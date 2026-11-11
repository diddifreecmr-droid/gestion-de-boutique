/**
 * Qui ouvre la section « Stock » et ce qu'il y fait (CDC § 4.2, UC-STK-05 à 10 ; backend
 * `application/stock/visibility.py`). Le serveur reste juge : ces droits servent seulement à ne
 * pas montrer une action interdite (CDC § 1.3). Fichier sans dépendance lourde : la coquille
 * l'importe au premier affichage.
 *
 * | Rôle | Matrice | Prix de base | Coûts, valeur | Historique, ajustement, inventaire |
 * | --- | --- | --- | --- | --- |
 * | Propriétaire | oui | oui | oui | oui |
 * | Comptable | oui | non | oui | oui |
 * | Vendeur | oui | oui | **jamais** | non |
 * | Chauffeur | aucun accès | | | |
 */
import type { Role } from "../../core/auth/me";

export type StockRole = "owner" | "accountant" | "seller";
export type ManagerRole = "owner" | "accountant";

/** Rôles qui ouvrent la section « Stock » (`STOCK_READ`). */
export const STOCK_ROLES: readonly Role[] = ["owner", "accountant", "seller"];

/** Rôle admis à la section ; tout autre rôle est une erreur de garde (fail-fast). */
export function stockRole(role: Role): StockRole {
  if (role === "owner" || role === "accountant" || role === "seller") return role;
  throw new Error(`Le rôle « ${role} » n'a pas accès au stock`);
}

/** Historique, ajustement, inventaire, valeur, abîmé, catalogue : propriétaire et comptable. */
export function isManager(role: StockRole): role is ManagerRole {
  return role !== "seller";
}
