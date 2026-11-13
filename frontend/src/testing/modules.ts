/** Modules de boutique pour les tests (décision client du 12/11/2026) : profils et jeux. */
import { ALL_MODULES, ALWAYS_ON, type ModuleCode } from "../core/profile/modules";
import { profileBody } from "./catalog";
import { json, SHOP_A, type Reply } from "./fakeApi";
import { saleProfile } from "./salesCatalog";

/** Boutique minimale : socle, journal, catalogue et ventes. */
export const MINIMAL: readonly ModuleCode[] = ALWAYS_ON;

/** Tous les modules sauf ceux nommés. */
export function without(...off: ModuleCode[]): ModuleCode[] {
  return ALL_MODULES.filter((module) => !off.includes(module));
}

export const PROFILE_ROUTE = `GET /api/v1/shops/${SHOP_A}/profile`;

/** Profil lu par la coquille avec ces modules actifs. */
export function profileWith(modules: readonly string[]): Record<string, Reply> {
  return { [PROFILE_ROUTE]: json(200, { ...profileBody("owner"), enabled_modules: modules }) };
}

/** Profil du faux serveur des ventes (lieu habituel, réglage du minimum) avec ces modules. */
export function saleProfileWith(
  role: "owner" | "seller",
  modules: readonly string[],
): Record<string, Reply> {
  return { [PROFILE_ROUTE]: json(200, { ...saleProfile(role), enabled_modules: modules }) };
}
