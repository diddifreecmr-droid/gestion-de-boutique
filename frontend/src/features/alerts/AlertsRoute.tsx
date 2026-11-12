import { useMemo } from "react";
import type { Role } from "../../core/auth/me";
import { AlertsContext, createHttpAlerts } from "../../core/gateways/httpAlerts";
import { useServices } from "../../core/services/servicesContext";
import { AlertsPage } from "./AlertsPage";

/** Entrée de route « Alertes » (cloche, chargée à la demande) : passerelle réelle. */
export default function AlertsRoute({ shopId, role }: { shopId: string; role: Role }) {
  const services = useServices();
  const gateway = useMemo(() => createHttpAlerts(services), [services]);
  return (
    <AlertsContext.Provider value={gateway}>
      <AlertsPage shopId={shopId} role={role} />
    </AlertsContext.Provider>
  );
}
