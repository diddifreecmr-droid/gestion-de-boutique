/**
 * Miroir, pour les tests, des menus et rôles servis par `GET /profile` (backend
 * `domain/profiles/motos.py` et `apparel.py`). Tests seulement : l'application, elle, ne lit
 * que la réponse du serveur.
 */
import type { components } from "../core/api/schema.gen";
import type { Role } from "../core/auth/me";

type Entry = components["schemas"]["MenuEntryResponse"];
export type ServedProfileCode = "motos" | "apparel" | "textile";

const e = (code: string, label: string, module: string, children: Entry[] = []): Entry => ({
  code,
  label,
  module,
  children,
});

const HOME = e("home", "Accueil", "dashboard");
const STOCK = e("stock", "Stock", "catalog");
const SELLER = [
  HOME,
  e("new_sale", "Nouvelle vente", "sales"),
  e("my_sales", "Mes ventes", "sales"),
  e("receivables", "Créances", "receivables"),
  STOCK,
];

const MOTOS: Partial<Record<Role, Entry[]>> = {
  owner: [
    HOME,
    e("sales", "Ventes", "sales"),
    STOCK,
    e("trucks", "Camions", "transport"),
    e("more", "Plus", "core", [
      e("receivables", "Créances", "receivables"),
      e("purchases", "Achats", "purchases"),
      e("expenses", "Dépenses", "expenses"),
      e("customers", "Clients", "sales"),
      e("payroll", "Paie", "transport"),
      e("audit", "Journal", "audit"),
      e("settings", "Réglages", "core"),
    ]),
  ],
  seller: SELLER,
  accountant: [
    HOME,
    e("purchases", "Achats", "purchases"),
    STOCK,
    e("transfers", "Déplacements", "transfers"),
    e("expenses", "Dépenses", "expenses"),
  ],
  driver: [
    e("my_trip", "Mon voyage", "transport"),
    e("my_trip_expenses", "Mes dépenses", "transport"),
    e("my_trips", "Mes voyages", "transport"),
  ],
};

const APPAREL: Partial<Record<Role, Entry[]>> = {
  owner: [
    HOME,
    e("sales", "Ventes", "sales"),
    STOCK,
    e("receivables", "Créances", "receivables"),
    e("more", "Plus", "core", [
      e("purchases", "Achats", "purchases"),
      e("expenses", "Dépenses", "expenses"),
      e("customers", "Clients", "sales"),
      e("audit", "Journal", "audit"),
      e("settings", "Réglages", "core"),
    ]),
  ],
  seller: SELLER,
  accountant: [
    HOME,
    e("purchases", "Achats", "purchases"),
    STOCK,
    e("expenses", "Dépenses", "expenses"),
    e("inventory", "Inventaire", "catalog"),
  ],
};

export const SERVED_MENUS: Readonly<Record<ServedProfileCode, Partial<Record<Role, Entry[]>>>> = {
  motos: MOTOS,
  apparel: APPAREL,
  textile: APPAREL,
};

const MOTOS_ROLES = { owner: "Propriétaire", seller: "Vendeur", accountant: "Comptable" };
export const SERVED_ROLES: Readonly<Record<ServedProfileCode, Partial<Record<Role, string>>>> = {
  motos: { ...MOTOS_ROLES, driver: "Chauffeur" },
  apparel: { ...MOTOS_ROLES, seller: "Employé" },
  textile: { ...MOTOS_ROLES, seller: "Employé" },
};

export function isServedCode(code: string): code is ServedProfileCode {
  return code === "motos" || code === "apparel" || code === "textile";
}

/** Menu du rôle sans les entrées d'un module éteint ; « Plus » vide disparaît (`visible_menu`). */
export function visibleMenu(entries: readonly Entry[], enabled: readonly string[]): Entry[] {
  return entries.flatMap((entry) => {
    const children = entry.children.filter((child) => enabled.includes(child.module));
    if (!enabled.includes(entry.module) || (entry.children.length > 0 && children.length === 0)) {
      return [];
    }
    return [{ ...entry, children }];
  });
}
