import { useMemo } from "react";
import type { Role } from "../../core/auth/me";
import { AppGatewaysProvider } from "../../core/gateways/GatewaysProvider";
import { createHttpReceivables, ReceivablesContext } from "../../core/gateways/httpReceivables";
import { useServices } from "../../core/services/servicesContext";
import { ReceivablesPage } from "./ReceivablesPage";
import { receivableRole } from "./receivablesNav";

/**
 * Entrée de route « Créances » (chargée à la demande) : passerelle réelle, horloge de
 * l'appareil, et passerelles des ventes pour la recherche / création rapide d'un client.
 */
export default function ReceivablesRoute({ shopId, role }: { shopId: string; role: Role }) {
  const services = useServices();
  const deps = useMemo(
    () => ({ gateway: createHttpReceivables(services), now: () => new Date() }),
    [services],
  );
  return (
    <AppGatewaysProvider>
      <ReceivablesContext.Provider value={deps}>
        <ReceivablesPage shopId={shopId} role={receivableRole(role)} />
      </ReceivablesContext.Provider>
    </AppGatewaysProvider>
  );
}
