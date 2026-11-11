/**
 * Passerelles simulées en mémoire : **vitrine `/_ui` seulement** (et le faux serveur des
 * tests, qui sert leurs règles en HTTP). Rien ne les importe depuis l'application : elles
 * n'entrent pas dans le build de production.
 */
import type { Gateways } from "../gateways";
import { createSimulatedCatalog } from "./simulatedCatalog";
import { createSimulatedSales } from "./simulatedSales";
import { createWorld, type SimulationOptions, type World } from "./world";

export function createSimulation(options: SimulationOptions): { world: World; gateways: Gateways } {
  const world = createWorld(options);
  const gateways = {
    catalog: createSimulatedCatalog(world),
    sales: createSimulatedSales(world),
    simulated: true,
  };
  return { world, gateways };
}

export function createSimulatedGateways(options: SimulationOptions): Gateways {
  return createSimulation(options).gateways;
}
