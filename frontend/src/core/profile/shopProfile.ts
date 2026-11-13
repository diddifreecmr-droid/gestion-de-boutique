/** Accès au profil d'une boutique et traduction des menus en entrées de navigation. */
import type { NavItem } from "../../shared/ui";
import type { Role } from "../auth/me";
import type { ShopModules } from "./modules";
import { MOTOS_PROFILE } from "./motos";
import { HOME_KEY, MORE_KEY, type MenuEntry, type ShopProfile } from "./types";

/**
 * PROVISOIRE : toutes les boutiques sont « Motos » tant que `GET /shops/{id}/profile`
 * n'existe pas (T10 / T12bis). L'appel remplacera ce corps, pas sa signature.
 */
export function profileForShop(shopId: string): ShopProfile {
  if (shopId === "") throw new Error("profileForShop : identifiant de boutique vide");
  return MOTOS_PROFILE;
}

/**
 * Le profil vu à travers les modules actifs : une entrée d'un module éteint disparaît de la
 * barre du bas et de « Plus » ; son adresse donne donc « Page introuvable » (`findSection`).
 */
export function withModules(profile: ShopProfile, modules: ShopModules): ShopProfile {
  const keep = (entries: readonly MenuEntry[]) =>
    entries.filter((entry) => entry.module === undefined || modules.has(entry.module));
  return {
    ...profile,
    menu: (role) => keep(profile.menu(role)),
    more: (role) => keep(profile.more(role)),
  };
}

export function shopPath(shopId: string, key: string = HOME_KEY): string {
  return key === HOME_KEY ? `/s/${shopId}` : `/s/${shopId}/${key}`;
}

export function navItems(profile: ShopProfile, role: Role, shopId: string): NavItem[] {
  return profile.menu(role).map((entry) => ({
    key: entry.key === HOME_KEY ? "accueil" : entry.key,
    label: entry.label,
    icon: entry.icon,
    href: shopPath(shopId, entry.key),
  }));
}

/** Entrée de menu à laquelle appartient une section (une page de « Plus » allume « Plus »). */
export function activeNavKey(profile: ShopProfile, role: Role, section: string): string | null {
  const keyOf = (entry: MenuEntry) => (entry.key === HOME_KEY ? "accueil" : entry.key);
  const direct = profile.menu(role).find((entry) => entry.key === section);
  if (direct !== undefined) return keyOf(direct);
  const inMore = profile.more(role).some((entry) => entry.key === section);
  const more = profile.menu(role).find((entry) => entry.key === MORE_KEY);
  return inMore && more !== undefined ? keyOf(more) : null;
}

/** La section est-elle visible pour ce rôle (barre du bas ou « Plus ») ? */
export function findSection(profile: ShopProfile, role: Role, section: string): MenuEntry | null {
  return (
    [...profile.menu(role), ...profile.more(role)].find((entry) => entry.key === section) ?? null
  );
}
