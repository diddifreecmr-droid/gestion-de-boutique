/**
 * Profil d'une boutique vu à travers ses modules, et traduction des menus en entrées de
 * navigation. Le profil lui-même vient du serveur : `profileFromResponse` (`servedProfile.ts`),
 * lu et gardé par `useShopProfile`.
 */
import type { NavItem } from "../../shared/ui";
import type { ShopModules } from "./modules";
import { HOME_KEY, MORE_KEY, type MenuEntry, type ShopProfile } from "./types";

/**
 * Le profil vu à travers les modules actifs : une entrée d'un module éteint disparaît de la
 * barre du bas et de « Plus » ; son adresse donne donc « Page introuvable » (`findSection`).
 * Le serveur filtre déjà son menu ; ce filtre garde la règle pour un profil gardé hors connexion.
 */
export function withModules(profile: ShopProfile, modules: ShopModules): ShopProfile {
  const keep = (entries: readonly MenuEntry[]) =>
    entries.filter((entry) => modules.has(entry.module));
  const more = keep(profile.more);
  // « Plus » vide disparaît (comme côté serveur).
  const menu = keep(profile.menu).filter((entry) => entry.key !== MORE_KEY || more.length > 0);
  return { ...profile, menu, more };
}

export function shopPath(shopId: string, key: string = HOME_KEY): string {
  return key === HOME_KEY ? `/s/${shopId}` : `/s/${shopId}/${key}`;
}

const navKey = (entry: MenuEntry) => (entry.key === HOME_KEY ? "accueil" : entry.key);

export function navItems(profile: ShopProfile, shopId: string): NavItem[] {
  return profile.menu.map((entry) => ({
    key: navKey(entry),
    label: entry.label,
    icon: entry.icon,
    href: shopPath(shopId, entry.key),
  }));
}

/** Entrée de menu à laquelle appartient une section (une page de « Plus » allume « Plus »). */
export function activeNavKey(profile: ShopProfile, section: string): string | null {
  const direct = profile.menu.find((entry) => entry.key === section);
  if (direct !== undefined) return navKey(direct);
  const inMore = profile.more.some((entry) => entry.key === section);
  const more = profile.menu.find((entry) => entry.key === MORE_KEY);
  return inMore && more !== undefined ? navKey(more) : null;
}

/** La section est-elle visible pour l'acteur (barre du bas ou « Plus ») ? */
export function findSection(profile: ShopProfile, section: string): MenuEntry | null {
  return [...profile.menu, ...profile.more].find((entry) => entry.key === section) ?? null;
}

/** Entrée d'accueil du rôle (« Accueil », « Mon voyage »), absente si le serveur ne la sert pas. */
export function homeEntry(profile: ShopProfile): MenuEntry | null {
  return profile.menu.find((entry) => entry.key === HOME_KEY) ?? null;
}
