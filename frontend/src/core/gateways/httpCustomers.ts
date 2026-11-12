/**
 * Passerelle réelle des Clients : `/api/v1/shops/{shop_id}/customers…` (T16). Rien n'est
 * avalé : `ApiError` et `NetworkError` remontent à l'écran.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { CustomersGateway } from "./customersContract";

const CUSTOMERS = "/api/v1/shops/{shop_id}/customers";
const CUSTOMER = "/api/v1/shops/{shop_id}/customers/{customer_id}";

export function createHttpCustomers({ api, session }: AppServices): CustomersGateway {
  const one = (shopId: string, id: string) => ({ shop_id: shopId, customer_id: id });
  return {
    search: async (shopId, query) => {
      const q = query.trim();
      const found = await session.authorized((token) =>
        api.get(CUSTOMERS, {
          token,
          params: { shop_id: shopId },
          query: { q: q === "" ? null : q },
        }),
      );
      return found.items;
    },
    sheet: (shopId, id) =>
      session.authorized((token) => api.get(CUSTOMER, { token, params: one(shopId, id) })),
    create: (shopId, body) =>
      session.authorized((token) =>
        api.post(CUSTOMERS, { token, params: { shop_id: shopId }, body }),
      ),
    update: (shopId, id, body) =>
      session.authorized((token) => api.patch(CUSTOMER, { token, params: one(shopId, id), body })),
  };
}

export const CustomersContext = createContext<CustomersGateway | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function useCustomersGateway(): CustomersGateway {
  const gateway = useContext(CustomersContext);
  if (gateway === null) {
    throw new Error("useCustomersGateway doit être appelé sous CustomersContext");
  }
  return gateway;
}
