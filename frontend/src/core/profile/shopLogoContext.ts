/**
 * Logo de la boutique active (specs § 15.1) : adresse affichée par la barre du haut, le
 * filigrane et l'aperçu des réglages. Servie par `GET /profile` (lien signé court, chargé
 * aussitôt) ; remplacée sur place quand le gérant envoie ou retire le logo, sans relire le profil.
 */
import { createContext, useContext } from "react";

export interface ShopLogoState {
  /** `null` : pas de logo, le logo générique (initiales) s'affiche. */
  src: string | null;
  replace: (src: string | null) => void;
}

export const ShopLogoContext = createContext<ShopLogoState | null>(null);

export function useShopLogo(): ShopLogoState {
  const state = useContext(ShopLogoContext);
  if (state === null) throw new Error("useShopLogo hors de la coquille d'une boutique");
  return state;
}

/** Profil gardé avant le 2026-11-24 : pas de champ `logo` → pas de logo. */
export function servedLogoPath(logo: { url: string } | null | undefined): string | null {
  return logo?.url ?? null;
}
