/**
 * Passerelle **réelle** des ventes : routes `/api/v1/shops/{shop_id}/…` (T16a), appels
 * authentifiés par `session.authorized` (refresh unique puis rejeu). Rien n'est avalé :
 * `ApiError` et `NetworkError` remontent à l'écran.
 *
 * SIMULÉ (T16b en cours côté serveur) : `requestPriceApproval`. La route des demandes de prix
 * n'existe pas encore ; la demande est gardée **en mémoire** et reste « en attente » (le
 * propriétaire ne peut pas encore y répondre). À brancher sur `POST /price-requests` en T16b.
 */
import { capturedAtHeader } from "../api/capturedAt";
import type { AppServices } from "../services/createServices";
import type { SalesGateway } from "./salesContract";

const SHOP = "/api/v1/shops/{shop_id}";
const SALE = "/api/v1/shops/{shop_id}/sales/{sale_id}";
const PRICE_REQUEST_TTL_MS = 30 * 60_000;

export function createHttpSales({ api, session }: AppServices): SalesGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const one = (shopId: string, id: string) => ({ shop_id: shopId, sale_id: id });
  return {
    recordSale: (shopId, command, capturedAt) => {
      const headers = { "X-Captured-At": capturedAtHeader(capturedAt) };
      return session.authorized((token) =>
        api.post(`${SHOP}/sales`, { token, params: shop(shopId), body: command, headers }),
      );
    },
    requestPriceApproval: (_shopId, command) => {
      const expires = new Date(Date.now() + PRICE_REQUEST_TTL_MS).toISOString();
      return Promise.resolve({ id: command.id, status: "pending", expires_at: expires });
    },
    searchCustomers: (shopId, query) => {
      const q = query.trim();
      if (q === "") return Promise.resolve({ items: [] });
      return session.authorized((token) =>
        api.get(`${SHOP}/customers`, { token, params: shop(shopId), query: { q } }),
      );
    },
    listSales: (shopId, filters, cursor) =>
      session.authorized((token) =>
        api.get(`${SHOP}/sales`, { token, params: shop(shopId), query: { ...filters, cursor } }),
      ),
    getSale: (shopId, id) =>
      session.authorized((token) => api.get(SALE, { token, params: one(shopId, id) })),
    cancelSale: (shopId, id, reason) =>
      session.authorized((token) =>
        api.post(`${SALE}/cancel`, {
          token,
          params: one(shopId, id),
          body: { reason, refund_payments: false },
        }),
      ),
    reportError: (shopId, id, body) =>
      session.authorized((token) =>
        api.post(`${SALE}/error-reports`, { token, params: one(shopId, id), body }),
      ),
    receipt: (shopId, id) =>
      session.authorized((token) => api.get(`${SALE}/receipt`, { token, params: one(shopId, id) })),
    members: (shopId) =>
      session.authorized((token) => api.get(`${SHOP}/members`, { token, params: shop(shopId) })),
  };
}
