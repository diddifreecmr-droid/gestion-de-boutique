/**
 * Lieu de la vente (Q-36 tranchée côté serveur) : le vendeur vend depuis **son** lieu habituel
 * (`default_location_id` du profil) ; le propriétaire choisit parmi les points de vente actifs
 * (présélection : son lieu habituel s'il en a un, sinon le premier dans l'ordre d'affichage).
 */
import type { Role } from "../../core/auth/me";
import type { SaleLocation, SaleSetup } from "../../core/gateways/catalogContract";

export type LocationChoice =
  | { status: "ready"; choices: SaleLocation[]; initial: SaleLocation }
  | { status: "none"; message: string };

export const NO_USUAL_LOCATION =
  "Aucun lieu de vente ne vous est attribué : demandez au propriétaire de vous rattacher à un point de vente.";
export const NO_POINT_OF_SALE =
  "La boutique n'a aucun point de vente actif : déclarez-en un dans les réglages des lieux.";

export function locationChoice(setup: SaleSetup, role: Role): LocationChoice {
  const usual = setup.locations.find((place) => place.id === setup.default_location_id);
  if (role !== "owner") {
    return usual === undefined
      ? { status: "none", message: NO_USUAL_LOCATION }
      : { status: "ready", choices: [usual], initial: usual };
  }
  const initial = usual ?? setup.locations[0];
  if (initial === undefined) return { status: "none", message: NO_POINT_OF_SALE };
  return { status: "ready", choices: setup.locations, initial };
}
