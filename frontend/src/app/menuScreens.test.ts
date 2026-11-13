/**
 * Audit UX du 13/11/2026 : aucune entrée de menu ne mène à un écran qui n'existe pas. Avec
 * **tous** les modules reçus du serveur (à venir compris), chaque entrée visible de chaque rôle
 * a son écran dans `SectionPage` — plus de page « Cet écran arrive bientôt ».
 */
import { describe, expect, it } from "vitest";
import { ROLES } from "../core/auth/me";
import { ALL_MODULES, shopModules, UPCOMING_MODULES } from "../core/profile/modules";
import { MOTOS_PROFILE } from "../core/profile/motos";
import { withModules } from "../core/profile/shopProfile";
import { HOME_KEY, MORE_KEY } from "../core/profile/types";
import { STOCK_KEY } from "../features/catalog/catalogRights";
import { EXPENSES_KEY } from "../features/expenses/expenseNav";
import { PURCHASES_KEY } from "../features/purchasing/purchasingNav";
import { RECEIVABLES_KEY } from "../features/receivables/receivablesNav";
import { MY_SALES_KEY, NEW_SALE_KEY, SALES_KEY } from "../features/sales/salesNav";
import { SETTINGS_KEY } from "../features/shopSettings/settingsNav";

/** Sections livrées, branchées dans `SectionPage` (« journal » et « clients » : « Plus »). */
const DELIVERED = new Set<string>([
  HOME_KEY,
  MORE_KEY,
  SALES_KEY,
  MY_SALES_KEY,
  NEW_SALE_KEY,
  STOCK_KEY,
  PURCHASES_KEY,
  RECEIVABLES_KEY,
  EXPENSES_KEY,
  SETTINGS_KEY,
  "journal",
  "clients",
]);

const visible = withModules(MOTOS_PROFILE, shopModules(ALL_MODULES));

describe("menus — aucune entrée sans écran (modules à venir)", () => {
  it.each(ROLES)("%s : chaque entrée visible (barre du bas et « Plus ») a son écran", (role) => {
    const keys = [...visible.menu(role), ...visible.more(role)].map((entry) => entry.key);
    expect(keys.filter((key) => !DELIVERED.has(key))).toEqual([]);
  });

  it.each(ROLES)("%s : aucune entrée d'un module à venir, même reçu du serveur", (role) => {
    const modules = [...visible.menu(role), ...visible.more(role)].map((entry) => entry.module);
    for (const upcoming of UPCOMING_MODULES) expect(modules).not.toContain(upcoming);
  });

  it("« Camions », « Paie », « Déplacements », « Mes voyages » : absents", () => {
    const labels = ROLES.flatMap((role) =>
      [...visible.menu(role), ...visible.more(role)].map((entry) => entry.label),
    );
    for (const gone of ["Camions", "Paie", "Déplacements", "Mes voyages", "Mes dépenses"]) {
      expect(labels).not.toContain(gone);
    }
  });
});
