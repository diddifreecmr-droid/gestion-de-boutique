/**
 * Passerelles des écrans (specs § 4.6) : l'écran dépend de ces interfaces, jamais de `fetch`.
 * L'application branche les passerelles **réelles** (`httpCatalog`, `httpSales`) ; la
 * simulation en mémoire ne sert plus qu'à la vitrine `/_ui` (aucun serveur derrière).
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { CatalogGateway } from "./catalogContract";
import { createHttpCatalog } from "./httpCatalog";
import { offlineDeps, withOfflineSales } from "../offline/offlineGateways";
import { createHttpSales } from "./httpSales";
import type { SalesGateway } from "./salesContract";

export interface Gateways {
  catalog: CatalogGateway;
  sales: SalesGateway;
  /** Vrai tant que les données viennent de la simulation (affiché à l'écran). */
  simulated: boolean;
}

/** Passerelles réelles : API de la boutique, jeton de la session. */
export function httpGateways(services: AppServices): Gateways {
  return {
    catalog: createHttpCatalog(services),
    // Vente : API, ou file hors connexion si `offline_capture` est actif (T23, RG-T22).
    sales: withOfflineSales(createHttpSales(services), offlineDeps(services)),
    simulated: false,
  };
}

const byServices = new WeakMap<AppServices, Gateways>();

/** Passerelles de l'application, une instance par jeu de services. */
export function appGateways(services: AppServices): Gateways {
  let gateways = byServices.get(services);
  if (gateways === undefined) {
    gateways = httpGateways(services);
    byServices.set(services, gateways);
  }
  return gateways;
}

export const GatewaysContext = createContext<Gateways | null>(null);

/** Hors d'un <GatewaysProvider>, c'est une erreur de câblage (fail-fast). */
export function useGateways(): Gateways {
  const gateways = useContext(GatewaysContext);
  if (gateways === null) throw new Error("useGateways doit être appelé sous un <GatewaysProvider>");
  return gateways;
}
