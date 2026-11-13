/**
 * Profil servi de la boutique active, lu par un écran **sous** la coquille de la boutique
 * (`ShopShell` le transmet par l'`Outlet`, `app/shopContext.ts`). Sert aux libellés qui
 * dépendent du type de boutique (T39) sans faire descendre le profil par chaque route.
 * Hors d'une boutique, c'est une erreur de câblage (fail-fast), jamais un profil inventé.
 */
import { useOutletContext } from "react-router";
import type { ShopProfile } from "./types";

function isProfile(value: unknown): value is ShopProfile {
  return (
    typeof value === "object" &&
    value !== null &&
    "roleLabel" in value &&
    "articleFields" in value &&
    "saleFields" in value
  );
}

export function useActiveProfile(): ShopProfile {
  const context: unknown = useOutletContext();
  const profile: unknown =
    typeof context === "object" && context !== null ? Reflect.get(context, "profile") : undefined;
  if (!isProfile(profile)) {
    throw new Error("useActiveProfile : écran rendu hors de la coquille d'une boutique");
  }
  return profile;
}
