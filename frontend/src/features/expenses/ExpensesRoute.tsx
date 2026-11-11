import { useMemo } from "react";
import type { Role } from "../../core/auth/me";
import { createHttpExpenses, ExpensesContext } from "../../core/gateways/httpExpenses";
import { useServices } from "../../core/services/servicesContext";
import { ExpensesPage } from "./ExpensesPage";

/**
 * Entrée de route « Dépenses » (chargée à la demande) : passerelle réelle branchée sur les
 * services de l'application, horloge de l'appareil.
 */
export default function ExpensesRoute({ shopId, role }: { shopId: string; role: Role }) {
  const services = useServices();
  const deps = useMemo(
    () => ({ gateway: createHttpExpenses(services), now: () => new Date() }),
    [services],
  );
  return (
    <ExpensesContext.Provider value={deps}>
      <ExpensesPage shopId={shopId} role={role} />
    </ExpensesContext.Provider>
  );
}
