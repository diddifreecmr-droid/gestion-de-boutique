/**
 * Profil de boutique vu par le frontend (specs § 4.5, TR-15), construit à partir de
 * `GET /shops/{id}/profile` (`servedProfile.ts`) : menus du rôle de l'acteur, libellés des rôles,
 * champs d'article et de vente. Point d'accès unique des écrans : `useActiveShop().profile`.
 */
import type { LucideIcon } from "lucide-react";
import type { components } from "../api/schema.gen";
import type { Role } from "../auth/me";
import type { ModuleCode } from "./modules";

export interface MenuEntry {
  /** Code stable servi par le profil (`home`, `sales`, `more`…). */
  code: string;
  /** Clé stable et segment d'URL : `/s/{shopId}/{key}` (l'accueil a la clé `""`). */
  key: string;
  /** Libellé servi par le profil (« Ventes », « Mon voyage »…). */
  label: string;
  icon: LucideIcon;
  /** Module dont dépend l'entrée : absente de la boutique si ce module est éteint. */
  module: ModuleCode;
}

/** Rôle proposé par le profil, avec son libellé (« Vendeur » ou « Employé »). */
export interface RoleChoice {
  role: Role;
  label: string;
}

/** Champ d'article ou de vente décrit par le profil (`FieldResponse`). */
export type ProfileField = components["schemas"]["FieldResponse"];

export interface ShopProfile {
  /** Code du profil (`motos`, `apparel`, `textile`). */
  code: string;
  label: string;
  version: number;
  /** Rôle de l'acteur pour qui le serveur a construit le menu. */
  role: Role;
  /** Rôles proposés par ce profil (un rôle absent n'existe pas dans la boutique). */
  roles: readonly RoleChoice[];
  /** Libellé d'un rôle du profil ; un rôle hors profil est une erreur (fail-fast). */
  roleLabel(role: Role): string;
  /** Barre du bas : au plus 5 entrées, celles du rôle de l'acteur (CDC § 1.3). */
  menu: readonly MenuEntry[];
  /** Contenu de l'entrée « Plus » (vide si le rôle n'en a pas). */
  more: readonly MenuEntry[];
  articleFields: readonly ProfileField[];
  saleFields: readonly ProfileField[];
  stockUnits: readonly string[];
  /** Règles de l'échange (QC-4, T42) : délai et autorisation de l'employé. */
  exchange: ExchangeRules;
}

/** Réglages d'échange servis par `GET /profile` (`exchange_days`, `employee_exchange_allowed`). */
export interface ExchangeRules {
  /** Délai en jours (inclusif, depuis la journée de la vente) ; `null` = aucune limite. */
  days: number | null;
  /** L'employé peut échanger ses ventes, dans le délai (désactivé par défaut). */
  employeeAllowed: boolean;
}

/** Clé de l'entrée « Plus » : elle ouvre la liste `more`. */
export const MORE_KEY = "plus";
/** Accueil du rôle : segment vide, `/s/{shopId}`. */
export const HOME_KEY = "";
