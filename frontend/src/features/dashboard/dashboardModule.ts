/**
 * Module `dashboard` de la boutique (specs § 15.1, « Modules par boutique ») : seul
 * l'administrateur plateforme l'active ; lu dans `enabled_modules` de `GET /shops/{id}/profile`.
 * Sans lui, aucun point d'entrée vers le tableau de bord complet n'apparaît. Module léger :
 * « Plus » et l'accueil l'importent sans charger l'écran.
 */
import { useState } from "react";
import type { AppServices } from "../../core/services/createServices";
import { useServices } from "../../core/services/servicesContext";
import { useLoad } from "../expenses/useLoad";
import type { Figures } from "./reportingContext";

export const DASHBOARD_MODULE = "dashboard";

/** Modules actifs de la boutique ; une réponse sans liste est une rupture de contrat. */
export async function enabledModules(
  { api, session }: AppServices,
  shopId: string,
): Promise<readonly string[]> {
  const profile = await session.authorized((token) =>
    api.get("/api/v1/shops/{shop_id}/profile", { token, params: { shop_id: shopId } }),
  );
  if (!Array.isArray(profile.enabled_modules)) {
    throw new Error(`Profil de la boutique ${shopId} sans « enabled_modules »`);
  }
  return profile.enabled_modules;
}

/**
 * Le module `dashboard` est-il actif ? Lu à chaque ouverture (l'administrateur peut le changer
 * à tout moment). Ce n'est pas un chiffre : une réponse lue reste valable si le réseau tombe
 * ensuite (le tableau de bord dit alors lui-même « Chiffres disponibles avec internet ») ; une
 * première lecture sans réseau donne « offline » et l'entrée reste cachée.
 */
export function useDashboardModule(shopId: string): Figures<boolean> {
  const services = useServices();
  const [attempt, setAttempt] = useState(0);
  const loaded = useLoad(`modules:${shopId}|${String(attempt)}`, async () =>
    (await enabledModules(services, shopId)).includes(DASHBOARD_MODULE),
  );
  return {
    loaded,
    retry: () => {
      setAttempt((current) => current + 1);
    },
  };
}
