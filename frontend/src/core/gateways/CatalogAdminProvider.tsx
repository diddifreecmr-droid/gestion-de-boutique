import type { ReactNode } from "react";
import { useServices } from "../services/servicesContext";
import { appCatalogAdmin, CatalogAdminContext } from "./catalogAdminContext";

/** Passerelle du catalogue de l'application (API réelle). */
export function CatalogAdminProvider({ children }: { children: ReactNode }) {
  const gateway = appCatalogAdmin(useServices());
  return <CatalogAdminContext.Provider value={gateway}>{children}</CatalogAdminContext.Provider>;
}
