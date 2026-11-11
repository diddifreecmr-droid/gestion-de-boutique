import { useEffect, type ReactNode } from "react";
import type { AppServices } from "./createServices";
import { ServicesContext } from "./servicesContext";

/** Fournit les services et lance, une fois, la restauration silencieuse de la session. */
export function ServicesProvider({
  services,
  children,
}: {
  services: AppServices;
  children: ReactNode;
}) {
  useEffect(() => {
    // restore() ne rejette que sur une valeur non-Error : elle remonte alors en clair.
    void services.session.restore();
  }, [services]);
  return <ServicesContext.Provider value={services}>{children}</ServicesContext.Provider>;
}
