/**
 * Passerelle réelle des Créances et versements : routes `/api/v1/shops/{shop_id}/…` (T17),
 * appels authentifiés par `session.authorized` (refresh unique puis rejeu). Rien n'est avalé :
 * `ApiError` et `NetworkError` remontent à l'écran.
 *
 * Le versement passe toujours par `POST /receivables/{id}/installments` : l'écran a déjà
 * désigné la créance (par défaut la plus ancienne du client, REC-03) et affiche le reste
 * après versement de **cette** créance avant validation.
 */
import { createContext, useContext } from "react";
import { capturedAtHeader } from "../api/capturedAt";
import type { AppServices } from "../services/createServices";
import type { ReceivableFilters, ReceivablesGateway } from "./receivablesContract";

const SHOP = "/api/v1/shops/{shop_id}";
const RECEIVABLE = "/api/v1/shops/{shop_id}/receivables/{receivable_id}";
const INSTALLMENT = "/api/v1/shops/{shop_id}/installments/{installment_id}";

export function createHttpReceivables({ api, session }: AppServices): ReceivablesGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const one = (shopId: string, id: string) => ({ shop_id: shopId, receivable_id: id });
  const paid = (shopId: string, id: string) => ({ shop_id: shopId, installment_id: id });
  return {
    list: (shopId, filters: ReceivableFilters) =>
      session.authorized((token) =>
        api.get(`${SHOP}/receivables`, { token, params: shop(shopId), query: { ...filters } }),
      ),
    get: (shopId, id) =>
      session.authorized((token) => api.get(RECEIVABLE, { token, params: one(shopId, id) })),
    recordLegacy: (shopId, body) =>
      session.authorized((token) =>
        api.post(`${SHOP}/receivables`, { token, params: shop(shopId), body }),
      ),
    change: (shopId, id, patch) =>
      session.authorized((token) =>
        api.patch(RECEIVABLE, { token, params: one(shopId, id), body: patch }),
      ),
    pay: (shopId, id, body, capturedAt) => {
      const headers = { "X-Captured-At": capturedAtHeader(capturedAt) };
      return session.authorized((token) =>
        api.post(`${RECEIVABLE}/installments`, { token, params: one(shopId, id), body, headers }),
      );
    },
    cancelInstallment: (shopId, id, reason) =>
      session.authorized((token) =>
        api.post(`${INSTALLMENT}/cancel`, { token, params: paid(shopId, id), body: { reason } }),
      ),
    receipt: (shopId, id) =>
      session.authorized((token) =>
        api.get(`${INSTALLMENT}/receipt`, { token, params: paid(shopId, id) }),
      ),
    writeOff: (shopId, id, reason) =>
      session.authorized((token) =>
        api.post(`${RECEIVABLE}/write-off`, { token, params: one(shopId, id), body: { reason } }),
      ),
    addReminder: (shopId, id, body) =>
      session.authorized((token) =>
        api.post(`${RECEIVABLE}/reminders`, { token, params: one(shopId, id), body }),
      ),
    changeReminder: (shopId, reminderId, patch) =>
      session.authorized((token) =>
        api.patch(`${SHOP}/reminders/{reminder_id}`, {
          token,
          params: { shop_id: shopId, reminder_id: reminderId },
          body: patch,
        }),
      ),
    addGuarantor: (shopId, id, body) =>
      session.authorized((token) =>
        api.post(`${RECEIVABLE}/guarantors`, { token, params: one(shopId, id), body }),
      ),
    statement: (shopId, customerId) =>
      session.authorized((token) =>
        api.get(`${SHOP}/customers/{customer_id}/statement`, {
          token,
          params: { shop_id: shopId, customer_id: customerId },
        }),
      ),
    searchCustomers: async (shopId, query) => {
      const q = query.trim();
      if (q === "") return [];
      const found = await session.authorized((token) =>
        api.get(`${SHOP}/customers`, { token, params: shop(shopId), query: { q } }),
      );
      return found.items;
    },
    paymentModes: (shopId) =>
      session.authorized((token) =>
        api.get(`${SHOP}/payment-modes`, { token, params: shop(shopId) }),
      ),
    members: (shopId) =>
      session.authorized((token) => api.get(`${SHOP}/members`, { token, params: shop(shopId) })),
  };
}

/** Passerelle et horloge des écrans Créances (l'horloge est remplacée dans les tests). */
export interface ReceivablesDeps {
  gateway: ReceivablesGateway;
  now: () => Date;
}

export const ReceivablesContext = createContext<ReceivablesDeps | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function useReceivablesDeps(): ReceivablesDeps {
  const deps = useContext(ReceivablesContext);
  if (deps === null) throw new Error("useReceivablesDeps doit être appelé sous ReceivablesContext");
  return deps;
}
