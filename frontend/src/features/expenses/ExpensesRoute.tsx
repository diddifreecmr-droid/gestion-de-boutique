import { useMemo } from "react";
import type { Role } from "../../core/auth/me";
import { createHttpExpenses, ExpensesContext } from "../../core/gateways/httpExpenses";
import { offlineDeps, withOfflineExpenses } from "../../core/offline/offlineGateways";
import { useServices } from "../../core/services/servicesContext";
import { ExpensesPage } from "./ExpensesPage";

/**
 * Entrée de route « Dépenses » (chargée à la demande) : passerelle réelle branchée sur les
 * services de l'application, horloge de l'appareil.
 */
export default function ExpensesRoute({ shopId, role }: { shopId: string; role: Role }) {
  const services = useServices();
  const deps = useMemo(
    () => ({
      // Dépense : API, ou file hors connexion si `offline_capture` est actif (T23, RG-T22).
      gateway: withOfflineExpenses(createHttpExpenses(services), offlineDeps(services)),
      now: () => new Date(),
    }),
    [services],
  );
  return (
    <ExpensesContext.Provider value={deps}>
      <ExpensesPage shopId={shopId} role={role} />
    </ExpensesContext.Provider>
  );
}
