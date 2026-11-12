/**
 * Passerelle réelle des Alertes : `/api/v1/shops/{shop_id}/alerts` (T09), appels authentifiés
 * par `session.authorized`. Rien n'est avalé : `ApiError` et `NetworkError` remontent à l'écran.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { AlertsGateway } from "./alertsContract";

const ALERTS = "/api/v1/shops/{shop_id}/alerts";

export function createHttpAlerts({ api, session }: AppServices): AlertsGateway {
  return {
    list: (shopId, { unreadOnly, cursor }) =>
      session.authorized((token) =>
        api.get(ALERTS, {
          token,
          params: { shop_id: shopId },
          query: { unread_only: unreadOnly ? true : null, cursor },
        }),
      ),
    markRead: async (shopId, alertId) => {
      const left = await session.authorized((token) =>
        api.post(`${ALERTS}/{alert_id}/read`, {
          token,
          params: { shop_id: shopId, alert_id: alertId },
        }),
      );
      return left.unread_count;
    },
  };
}

export const AlertsContext = createContext<AlertsGateway | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function useAlertsGateway(): AlertsGateway {
  const gateway = useContext(AlertsContext);
  if (gateway === null) throw new Error("useAlertsGateway doit être appelé sous AlertsContext");
  return gateway;
}
