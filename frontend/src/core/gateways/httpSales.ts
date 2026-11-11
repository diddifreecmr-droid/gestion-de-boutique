/**
 * Passerelle **réelle** des ventes : routes `/api/v1/shops/{shop_id}/…` (T16a, T16b), appels
 * authentifiés par `session.authorized` (refresh unique puis rejeu). Rien n'est avalé :
 * `ApiError` et `NetworkError` remontent à l'écran. Demandes de prix : `/price-requests`
 * (création, liste, lecture, décision) ; retours : `/sales/{id}/returns`.
 */
import { capturedAtHeader } from "../api/capturedAt";
import type { AppServices } from "../services/createServices";
import type { SalesGateway } from "./salesContract";

const SHOP = "/api/v1/shops/{shop_id}";
const SALE = "/api/v1/shops/{shop_id}/sales/{sale_id}";
const PRICE = "/api/v1/shops/{shop_id}/price-requests/{request_id}";

export function createHttpSales({ api, session }: AppServices): SalesGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const one = (shopId: string, id: string) => ({ shop_id: shopId, sale_id: id });
  const request = (shopId: string, id: string) => ({ shop_id: shopId, request_id: id });
  return {
    recordSale: (shopId, command, capturedAt) => {
      const headers = { "X-Captured-At": capturedAtHeader(capturedAt) };
      return session.authorized((token) =>
        api.post(`${SHOP}/sales`, { token, params: shop(shopId), body: command, headers }),
      );
    },
    requestPriceApproval: (shopId, command) =>
      session.authorized((token) =>
        api.post(`${SHOP}/price-requests`, { token, params: shop(shopId), body: command }),
      ),
    listPriceRequests: (shopId) =>
      session.authorized((token) =>
        api.get(`${SHOP}/price-requests`, { token, params: shop(shopId) }),
      ),
    getPriceRequest: (shopId, id) =>
      session.authorized((token) => api.get(PRICE, { token, params: request(shopId, id) })),
    decidePriceRequest: (shopId, id, decision, version) =>
      session.authorized((token) =>
        api.post(`${PRICE}/decision`, {
          token,
          params: request(shopId, id),
          body: { decision, version },
        }),
      ),
    recordReturn: (shopId, id, command) =>
      session.authorized((token) =>
        api.post(`${SALE}/returns`, { token, params: one(shopId, id), body: command }),
      ),
    listReturns: (shopId, id) =>
      session.authorized((token) => api.get(`${SALE}/returns`, { token, params: one(shopId, id) })),
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
