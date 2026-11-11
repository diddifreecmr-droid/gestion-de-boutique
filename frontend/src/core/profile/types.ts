/**
 * Profil de boutique vu par le frontend (specs § 4.5, TR-15) : menus par rôle, libellés.
 * La source définitive sera `GET /shops/{id}/profile` (T10 / T12bis) ; seule l'implémentation
 * changera, pas cette interface.
 */
import type { LucideIcon } from "lucide-react";
import type { Role } from "../auth/me";

export interface MenuEntry {
  /** Clé stable et segment d'URL : `/s/{shopId}/{key}` (l'accueil a la clé `""`). */
  key: string;
  label: string;
  icon: LucideIcon;
}

export interface ShopProfile {
  /** Code du profil (`motos`, puis `pret-a-porter`, `textile`). */
  code: string;
  /** Vrai tant que le profil ne vient pas de l'API (implémentation statique). */
  provisional: boolean;
  roleLabel(role: Role): string;
  /** Barre du bas : au plus 5 entrées, celles que le rôle a le droit de voir (CDC § 1.3). */
  menu(role: Role): readonly MenuEntry[];
  /** Contenu de l'entrée « Plus » (vide si le rôle n'en a pas). */
  more(role: Role): readonly MenuEntry[];
}

/** Clé de l'entrée « Plus » : elle ouvre la liste `more(role)`. */
export const MORE_KEY = "plus";
/** Accueil du rôle : segment vide, `/s/{shopId}`. */
export const HOME_KEY = "";
