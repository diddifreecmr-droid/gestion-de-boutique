/**
 * Passerelle **réelle** du Stock : routes `/api/v1/shops/{shop_id}/…` (T14), appels
 * authentifiés par `session.authorized` (refresh unique puis rejeu). Rien n'est avalé :
 * `ApiError` et `NetworkError` remontent à l'écran.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { StockGateway } from "./stockContract";

const SHOP = "/api/v1/shops/{shop_id}";
const INVENTORY = "/api/v1/shops/{shop_id}/inventories/{inventory_id}";

export function createHttpStock({ api, session }: AppServices): StockGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const inv = (shopId: string, id: string) => ({ shop_id: shopId, inventory_id: id });
  return {
    matrix: (shopId, { text, locationId, sort }) => {
      const q = text.trim();
      return session.authorized((token) =>
        api.get(`${SHOP}/stock`, {
          token,
          params: shop(shopId),
          query: { q: q === "" ? null : q, location_id: locationId, sort },
        }),
      );
    },
    value: (shopId) =>
      session.authorized((token) =>
        api.get(`${SHOP}/stock/value`, { token, params: shop(shopId) }),
      ),
    damaged: (shopId) =>
      session.authorized((token) =>
        api.get(`${SHOP}/stock/damaged`, { token, params: shop(shopId) }),
      ),
    movements: (shopId, articleId, cursor) =>
      session.authorized((token) =>
        api.get(`${SHOP}/articles/{article_id}/movements`, {
          token,
          params: { shop_id: shopId, article_id: articleId },
          query: { cursor },
        }),
      ),
    articleName: async (shopId, articleId) => {
      const article = await session.authorized((token) =>
        api.get(`${SHOP}/articles/{article_id}`, {
          token,
          params: { shop_id: shopId, article_id: articleId },
        }),
      );
      return article.display_name;
    },
    adjust: (shopId, body) =>
      session.authorized((token) =>
        api.post(`${SHOP}/adjustments`, { token, params: shop(shopId), body }),
      ),
    startInventory: (shopId, id, locationId) =>
      session.authorized((token) =>
        api.post(`${SHOP}/inventories`, {
          token,
          params: shop(shopId),
          body: { id, location_id: locationId },
        }),
      ),
    inventory: (shopId, id) =>
      session.authorized((token) => api.get(INVENTORY, { token, params: inv(shopId, id) })),
    saveCounts: (shopId, id, body) =>
      session.authorized((token) =>
        api.put(`${INVENTORY}/counts`, { token, params: inv(shopId, id), body }),
      ),
    validateInventory: (shopId, id, body) =>
      session.authorized((token) =>
        api.post(`${INVENTORY}/validate`, { token, params: inv(shopId, id), body }),
      ),
    abandonInventory: (shopId, id, version) =>
      session.authorized((token) =>
        api.post(`${INVENTORY}/abandon`, { token, params: inv(shopId, id), body: { version } }),
      ),
    members: (shopId) =>
      session.authorized((token) => api.get(`${SHOP}/members`, { token, params: shop(shopId) })),
  };
}

export const StockContext = createContext<StockGateway | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function useStockGateway(): StockGateway {
  const gateway = useContext(StockContext);
  if (gateway === null) throw new Error("useStockGateway doit être appelé sous StockContext");
  return gateway;
}
