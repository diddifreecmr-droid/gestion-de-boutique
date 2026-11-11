/**
 * Passerelles des écrans (specs § 4.6) : l'écran dépend de ces interfaces, jamais de `fetch`.
 * En attendant `POST /sales` (T16), l'application branche la simulation ; T21 remplacera
 * `createSimulatedGateways` par les passerelles réelles sans toucher aux écrans.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { CatalogGateway } from "./catalogContract";
import type { SalesGateway } from "./salesContract";
import { createSimulatedCatalog } from "./simulated/simulatedCatalog";
import { createSimulatedSales } from "./simulated/simulatedSales";
import { createWorld, type SimulationOptions } from "./simulated/world";

export interface Gateways {
  catalog: CatalogGateway;
  sales: SalesGateway;
  /** Vrai tant que les données viennent de la simulation (affiché à l'écran). */
  simulated: boolean;
}

export function createSimulatedGateways(options: SimulationOptions): Gateways {
  const world = createWorld(options);
  return {
    catalog: createSimulatedCatalog(world),
    sales: createSimulatedSales(world),
    simulated: true,
  };
}

/** Simulation branchée sur les services : réseau réel et rôle lu dans la session ouverte. */
export function simulatedAppGateways(services: AppServices): Gateways {
  return createSimulatedGateways({
    isOnline: () => services.connectivity.online,
    onNetworkFailure: () => {
      services.connectivity.reportNetworkFailure();
    },
    roleIn: (shopId) => {
      const state = services.session.state.get();
      const shop =
        state.status === "signedIn"
          ? state.me.shops.find((membership) => membership.shopId === shopId)
          : undefined;
      if (shop === undefined) throw new Error(`Aucun rôle dans la boutique « ${shopId} »`);
      return shop.role;
    },
  });
}

const byServices = new WeakMap<AppServices, Gateways>();

/**
 * Passerelles de l'application. PROVISOIRE (T21) : la simulation, en attendant les routes
 * des ventes ; les passerelles réelles prendront sa place ici, sans toucher aux écrans.
 * Une instance par jeu de services : la simulation garde ses ventes d'un écran à l'autre.
 */
export function appGateways(services: AppServices): Gateways {
  let gateways = byServices.get(services);
  if (gateways === undefined) {
    gateways = simulatedAppGateways(services);
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
