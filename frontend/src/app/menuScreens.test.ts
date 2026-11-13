/**
 * Audit UX du 13/11/2026 : aucune entrée de menu ne mène à un écran qui n'existe pas. Avec
 * **tous** les modules reçus du serveur (à venir compris), chaque entrée visible de chaque rôle
 * de chaque profil (Motos, Prêt-à-porter, Textile) a son écran dans `SectionPage`.
 */
import { describe, expect, it } from "vitest";
import type { Role } from "../core/auth/me";
import { INVENTORY_KEY } from "../core/profile/menuRoutes";
import { ALL_MODULES, shopModules, UPCOMING_MODULES } from "../core/profile/modules";
import { profileFromResponse } from "../core/profile/servedProfile";
import { withModules } from "../core/profile/shopProfile";
import { HOME_KEY, MORE_KEY } from "../core/profile/types";
import { STOCK_KEY } from "../features/catalog/catalogRights";
import { EXPENSES_KEY } from "../features/expenses/expenseNav";
import { PURCHASES_KEY } from "../features/purchasing/purchasingNav";
import { RECEIVABLES_KEY } from "../features/receivables/receivablesNav";
import { MY_SALES_KEY, NEW_SALE_KEY, SALES_KEY } from "../features/sales/salesNav";
import { IMPORTS_KEY } from "../features/imports/importsNav";
import { SETTINGS_KEY } from "../features/shopSettings/settingsNav";
import type { ServedProfileCode } from "../testing/profileMenus";
import { servedProfile } from "../testing/servedProfile";

/** Sections livrées, branchées dans `SectionPage` (« journal » et « clients » : « Plus »). */
const DELIVERED = new Set<string>([
  HOME_KEY,
  MORE_KEY,
  SALES_KEY,
  MY_SALES_KEY,
  NEW_SALE_KEY,
  STOCK_KEY,
  INVENTORY_KEY,
  PURCHASES_KEY,
  RECEIVABLES_KEY,
  EXPENSES_KEY,
  SETTINGS_KEY,
  IMPORTS_KEY,
  "journal",
  "clients",
]);

const CASES: [ServedProfileCode, Role][] = [
  ["motos", "owner"],
  ["motos", "seller"],
  ["motos", "accountant"],
  ["motos", "driver"],
  ["apparel", "owner"],
  ["apparel", "seller"],
  ["apparel", "accountant"],
  ["textile", "owner"],
  ["textile", "seller"],
  ["textile", "accountant"],
];

function visible(code: ServedProfileCode, role: Role) {
  const served = profileFromResponse(servedProfile(code, role, ALL_MODULES), role);
  const profile = withModules(served, shopModules(ALL_MODULES));
  return [...profile.menu, ...profile.more];
}

describe("menus — aucune entrée sans écran (modules à venir)", () => {
  it.each(CASES)("%s, %s : chaque entrée visible a son écran", (code, role) => {
    const keys = visible(code, role).map((entry) => entry.key);
    expect(keys.filter((key) => !DELIVERED.has(key))).toEqual([]);
  });

  it.each(CASES)("%s, %s : aucune entrée d'un module à venir, même reçu", (code, role) => {
    const modules = visible(code, role).map((entry) => entry.module);
    for (const upcoming of UPCOMING_MODULES) expect(modules).not.toContain(upcoming);
  });

  it("« Camions », « Paie », « Déplacements », « Mes voyages » : absents", () => {
    const labels = CASES.flatMap(([code, role]) => visible(code, role).map((e) => e.label));
    for (const gone of ["Camions", "Paie", "Déplacements", "Mes voyages", "Mes dépenses"]) {
      expect(labels).not.toContain(gone);
    }
  });
});
