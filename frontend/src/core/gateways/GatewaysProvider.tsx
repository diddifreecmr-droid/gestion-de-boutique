import type { ReactNode } from "react";
import { useServices } from "../services/servicesContext";
import { appGateways, GatewaysContext, type Gateways } from "./gateways";

/** Fournit des passerelles données (tests, vitrine). */
export function GatewaysProvider({
  gateways,
  children,
}: {
  gateways: Gateways;
  children: ReactNode;
}) {
  return <GatewaysContext.Provider value={gateways}>{children}</GatewaysContext.Provider>;
}

/**
 * Passerelles de l'application, une seule fois par jeu de services. Importé seulement par
 * les écrans chargés à la demande : la simulation ne pèse pas sur le premier affichage.
 */
export function AppGatewaysProvider({ children }: { children: ReactNode }) {
  const gateways = appGateways(useServices());
  return <GatewaysProvider gateways={gateways}>{children}</GatewaysProvider>;
}
