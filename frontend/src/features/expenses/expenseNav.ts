import type { Role } from "../../core/auth/me";
import type { References } from "./references";

/** Segment d'URL de la section (clé du menu comptable et du « Plus » propriétaire, § 17.4). */
export const EXPENSES_KEY = "depenses";

/** Rôles qui voient les dépenses (matrice `EXPENSE_READ` : propriétaire et comptable). */
export const EXPENSE_ROLES: readonly Role[] = ["owner", "accountant"];

/** Valeurs de `?vue=` dans la section. */
export const VIEW = {
  create: "nouvelle",
  detail: "fiche",
  edit: "modifier",
  settings: "reglages",
} as const;

export interface ExpenseNav {
  list: () => void;
  open: (id: string) => void;
  /** Nouvelle dépense ; `repeatOf` = « Refaire cette dépense » à partir de celle-ci. */
  create: (repeatOf?: string) => void;
  edit: (id: string) => void;
  settings: () => void;
}

/** Ce que reçoit chaque écran de la section. */
export interface ScreenProps {
  shopId: string;
  refs: References;
  nav: ExpenseNav;
}
