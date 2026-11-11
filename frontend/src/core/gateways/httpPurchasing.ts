/**
 * Passerelle **réelle** des Achats : routes `/api/v1/shops/{shop_id}/…` (T15), appels
 * authentifiés par `session.authorized` (refresh unique puis rejeu). Rien n'est avalé :
 * `ApiError` et `NetworkError` remontent à l'écran.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { CatalogAdminGateway } from "./catalogAdminContract";
import type { PurchasingGateway } from "./purchasingContract";

const SHOP = "/api/v1/shops/{shop_id}";
const PURCHASE = "/api/v1/shops/{shop_id}/purchases/{purchase_id}";
const SUPPLIER = "/api/v1/shops/{shop_id}/suppliers/{supplier_id}";

export function createHttpPurchasing({ api, session }: AppServices): PurchasingGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const one = (shopId: string, id: string) => ({ shop_id: shopId, purchase_id: id });
  const supplier = (shopId: string, id: string) => ({ shop_id: shopId, supplier_id: id });
  return {
    list: (shopId, filters, cursor) =>
      session.authorized((token) =>
        api.get(`${SHOP}/purchases`, {
          token,
          params: shop(shopId),
          query: { ...filters, cursor },
        }),
      ),
    get: (shopId, id) =>
      session.authorized((token) => api.get(PURCHASE, { token, params: one(shopId, id) })),
    record: (shopId, body) =>
      session.authorized((token) =>
        api.post(`${SHOP}/purchases`, { token, params: shop(shopId), body }),
      ),
    correct: (shopId, id, patch) =>
      session.authorized((token) =>
        api.patch(PURCHASE, { token, params: one(shopId, id), body: patch }),
      ),
    cancel: (shopId, id, reason) =>
      session.authorized((token) =>
        api.post(`${PURCHASE}/cancel`, { token, params: one(shopId, id), body: { reason } }),
      ),
    pay: (shopId, id, body) =>
      session.authorized((token) =>
        api.post(`${PURCHASE}/payments`, { token, params: one(shopId, id), body }),
      ),
    suppliers: async (shopId) => {
      const found = await session.authorized((token) =>
        api.get(`${SHOP}/suppliers`, { token, params: shop(shopId) }),
      );
      return found.items;
    },
    createSupplier: (shopId, body) =>
      session.authorized((token) =>
        api.post(`${SHOP}/suppliers`, { token, params: shop(shopId), body }),
      ),
    updateSupplier: (shopId, id, patch) =>
      session.authorized((token) =>
        api.patch(SUPPLIER, { token, params: supplier(shopId, id), body: patch }),
      ),
    supplierSheet: (shopId, id, period) =>
      session.authorized((token) =>
        api.get(SUPPLIER, { token, params: supplier(shopId, id), query: { ...period } }),
      ),
    locations: async (shopId) => {
      const found = await session.authorized((token) =>
        api.get(`${SHOP}/locations`, { token, params: shop(shopId) }),
      );
      return found.items;
    },
    paymentModes: (shopId) =>
      session.authorized((token) =>
        api.get(`${SHOP}/payment-modes`, { token, params: shop(shopId) }),
      ),
    receptionLocation: async (shopId) => {
      const settings = await session.authorized((token) =>
        api.get(`${SHOP}/settings`, { token, params: shop(shopId) }),
      );
      return settings.reception_location_id;
    },
  };
}

/**
 * Dépendances des écrans Achats : la passerelle, celle du catalogue (recherche et création
 * d'article sans quitter la saisie) et l'horloge (remplacée dans les tests).
 */
export interface PurchasingDeps {
  gateway: PurchasingGateway;
  catalog: CatalogAdminGateway;
  now: () => Date;
}

export const PurchasingContext = createContext<PurchasingDeps | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function usePurchasingDeps(): PurchasingDeps {
  const deps = useContext(PurchasingContext);
  if (deps === null) throw new Error("usePurchasingDeps doit être appelé sous PurchasingContext");
  return deps;
}
