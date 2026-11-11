import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { CatalogAdminGateway } from "./catalogAdminContract";
import { createHttpCatalogAdmin } from "./httpCatalogAdmin";

export const CatalogAdminContext = createContext<CatalogAdminGateway | null>(null);

const byServices = new WeakMap<AppServices, CatalogAdminGateway>();

/** Passerelle réelle, une par jeu de services. */
export function appCatalogAdmin(services: AppServices): CatalogAdminGateway {
  let gateway = byServices.get(services);
  if (gateway === undefined) {
    gateway = createHttpCatalogAdmin(services);
    byServices.set(services, gateway);
  }
  return gateway;
}

/** Hors d'un <CatalogAdminProvider>, c'est une erreur de câblage (fail-fast). */
export function useCatalogAdmin(): CatalogAdminGateway {
  const gateway = useContext(CatalogAdminContext);
  if (gateway === null) {
    throw new Error("useCatalogAdmin doit être appelé sous un <CatalogAdminProvider>");
  }
  return gateway;
}
