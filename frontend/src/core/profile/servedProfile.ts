/**
 * `GET /shops/{id}/profile` → `ShopProfile` (fin du profil Motos écrit en dur, T37). Tout vient
 * du serveur : menus du rôle de l'acteur (déjà sans les entrées d'un module éteint), libellés,
 * rôles proposés, champs. Ce qui n'est pas servi n'est pas inventé ; ce qui est servi mais
 * inconnu (code de menu, module, rôle) est une rupture de contrat : erreur explicite.
 */
import type { components } from "../api/schema.gen";
import { parseRole, type Role } from "../auth/me";
import { menuRoute } from "./menuRoutes";
import { parseModule } from "./modules";
import { MORE_KEY, type MenuEntry, type RoleChoice, type ShopProfile } from "./types";

export type ProfileResponse = components["schemas"]["ProfileResponse"];
type ServedEntry = components["schemas"]["MenuEntryResponse"];

function entryOf(served: ServedEntry): MenuEntry {
  const { key, icon } = menuRoute(served.code);
  return { code: served.code, key, label: served.label, icon, module: parseModule(served.module) };
}

/** Menu servi → barre du bas et « Plus » (seule l'entrée « Plus » a des sous-entrées). */
function menusOf(served: readonly ServedEntry[]): { menu: MenuEntry[]; more: MenuEntry[] } {
  const menu = served.map(entryOf);
  const parents = served.filter((entry) => entry.children.length > 0);
  for (const parent of parents) {
    if (menuRoute(parent.code).key !== MORE_KEY) {
      throw new Error(`Menu servi : seule l'entrée « Plus » a des sous-entrées (${parent.code})`);
    }
  }
  if (parents.length > 1) throw new Error("Menu servi : plusieurs entrées « Plus »");
  const more = parents[0]?.children.map(entryOf) ?? [];
  const keys = [...menu, ...more].map((entry) => entry.key);
  if (new Set(keys).size !== keys.length) {
    throw new Error(`Menu servi : sections en double (${keys.join(", ")})`);
  }
  return { menu, more };
}

/**
 * Profil de la boutique pour l'acteur `role` (son rôle d'après `GET /me`). Le serveur doit avoir
 * construit le menu pour ce même rôle : sinon la réponse ne le concerne pas (fail-fast).
 */
export function profileFromResponse(response: ProfileResponse, role: Role): ShopProfile {
  if (response.role !== role) {
    throw new Error(
      `Profil servi pour le rôle « ${String(response.role)} », attendu « ${role} » (GET /profile)`,
    );
  }
  const roles: RoleChoice[] = response.roles.map((choice) => ({
    role: parseRole(choice.code),
    label: choice.label,
  }));
  if (!roles.some((choice) => choice.role === role)) {
    throw new Error(`Rôle « ${role} » absent des rôles du profil « ${response.profile_code} »`);
  }
  const roleLabel = (wanted: Role): string => {
    const found = roles.find((choice) => choice.role === wanted);
    if (found === undefined) {
      throw new Error(`Rôle « ${wanted} » absent du profil « ${response.profile_code} »`);
    }
    return found.label;
  };
  return {
    code: response.profile_code,
    label: response.profile_label,
    version: response.profile_version,
    role,
    roles,
    roleLabel,
    ...menusOf(response.menu),
    articleFields: response.article_fields,
    saleFields: response.sale_fields,
    stockUnits: response.stock_units,
  };
}
