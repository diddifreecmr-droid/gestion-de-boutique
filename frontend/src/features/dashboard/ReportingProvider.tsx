import { useMemo, type ReactNode } from "react";
import { createHttpReporting } from "../../core/gateways/httpReporting";
import { useServices } from "../../core/services/servicesContext";
import { ReportingContext } from "./reportingContext";

/** Passerelle réelle des chiffres, branchée sur les services de l'application ; horloge de l'appareil. */
export function ReportingProvider({ children }: { children: ReactNode }) {
  const services = useServices();
  const deps = useMemo(
    () => ({ gateway: createHttpReporting(services), now: () => new Date() }),
    [services],
  );
  return <ReportingContext.Provider value={deps}>{children}</ReportingContext.Provider>;
}
