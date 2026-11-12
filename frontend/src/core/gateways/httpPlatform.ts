/**
 * Passerelle réelle de la console plateforme : `/api/v1/platform/shops…` (T10). Rien n'est
 * avalé : `ApiError` et `NetworkError` remontent à l'écran.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { PlatformGateway } from "./platformContract";

const SHOPS = "/api/v1/platform/shops";
const SHOP = "/api/v1/platform/shops/{shop_id}";

export function createHttpPlatform({ api, session }: AppServices): PlatformGateway {
  const one = (shopId: string) => ({ shop_id: shopId });
  return {
    list: () => session.authorized((token) => api.get(SHOPS, { token })),
    open: (body) => session.authorized((token) => api.post(SHOPS, { token, body })),
    get: (shopId) => session.authorized((token) => api.get(SHOP, { token, params: one(shopId) })),
    administer: (shopId, body) =>
      session.authorized((token) => api.patch(SHOP, { token, params: one(shopId), body })),
    access: (shopId) =>
      session.authorized((token) => api.get(`${SHOP}/access`, { token, params: one(shopId) })),
  };
}

export const PlatformContext = createContext<PlatformGateway | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function usePlatformGateway(): PlatformGateway {
  const gateway = useContext(PlatformContext);
  if (gateway === null) throw new Error("usePlatformGateway doit être appelé sous PlatformContext");
  return gateway;
}
