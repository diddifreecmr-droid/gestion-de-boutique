/**
 * Section « Créances » : entrée du vendeur et « Plus → Créances » du propriétaire (CDC § 17.4).
 * La vue est dans l'adresse (`?vue=…&id=…`) : le bouton retour du téléphone revient en arrière.
 */
import type { Role } from "../../core/auth/me";
import type { References } from "./references";

/** Segment d'URL de la section. */
export const RECEIVABLES_KEY = "creances";

/** Rôles admis (comptable et chauffeur : aucun accès, CDC § 10). */
export const RECEIVABLE_ROLES: readonly Role[] = ["owner", "seller"];

export type ReceivableRole = "owner" | "seller";

/** Rôle admis à la section ; tout autre rôle est une erreur de garde (fail-fast). */
export function receivableRole(role: Role): ReceivableRole {
  if (role === "owner" || role === "seller") return role;
  throw new Error(`Le rôle « ${role} » n'accède pas aux créances (garde de route manquante)`);
}

/** Valeurs de `?vue=` dans la section. */
export const VIEW = {
  detail: "fiche",
  pay: "versement",
  legacy: "ancienne",
  statement: "releve",
} as const;

/** Adresse relative de « Enregistrer un versement » (recherche du client, UC-CRE-03). */
export const PAY_SEARCH = `?vue=${VIEW.pay}`;

export interface ReceivableNav {
  list: () => void;
  open: (id: string) => void;
  /** Versement : sur une créance donnée, sinon recherche du client (UC-CRE-03). */
  pay: (receivableId?: string) => void;
  legacy: () => void;
  statement: (customerId: string) => void;
}

/** Ce que reçoit chaque écran de la section. */
export interface ScreenProps {
  shopId: string;
  refs: References;
  nav: ReceivableNav;
}
