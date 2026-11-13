/**
 * Dernier profil lu de chaque boutique (`GET /shops/{id}/profile`), gardé dans `localStorage`
 * pour ouvrir la boutique **sans réseau**. Une valeur mal formée est une erreur explicite.
 */
import type { Role } from "../auth/me";
import type { ProfileResponse } from "./servedProfile";

export const PROFILE_KEY = "boutique.shop-profile";

type Saved = Record<string, ProfileResponse>;

const isStringArray = (value: unknown) =>
  Array.isArray(value) && value.every((item) => typeof item === "string");

function looksLikeProfile(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const profile = value as Partial<Record<keyof ProfileResponse, unknown>>;
  return (
    typeof profile.profile_code === "string" &&
    (typeof profile.role === "string" || profile.role === null) &&
    isStringArray(profile.enabled_modules) &&
    Array.isArray(profile.menu) &&
    Array.isArray(profile.roles) &&
    Array.isArray(profile.article_fields) &&
    Array.isArray(profile.sale_fields)
  );
}

function readSaved(): Saved {
  const text = window.localStorage.getItem(PROFILE_KEY);
  if (text === null) return {};
  const value: unknown = JSON.parse(text);
  const valid =
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.values(value).every(looksLikeProfile);
  if (!valid) throw new Error(`Profils gardés mal formés dans « ${PROFILE_KEY} »`);
  return value as Saved;
}

export function saveProfile(shopId: string, profile: ProfileResponse): void {
  window.localStorage.setItem(PROFILE_KEY, JSON.stringify({ ...readSaved(), [shopId]: profile }));
}

/**
 * Profil gardé pour `shopId`, s'il a été lu pour ce même rôle (un rôle changé depuis rend
 * l'ancien menu faux : il n'est pas réutilisé).
 */
export function savedProfile(shopId: string, role: Role): ProfileResponse | null {
  const saved = readSaved()[shopId];
  return saved?.role === role ? saved : null;
}
