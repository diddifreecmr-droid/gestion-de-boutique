/**
 * Passerelle réelle des Réglages de la boutique : routes `/api/v1/shops/{shop_id}/…` (T10),
 * appels authentifiés par `session.authorized` (refresh unique puis rejeu). Rien n'est
 * avalé : `ApiError` et `NetworkError` remontent à l'écran.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { ShopAdminGateway } from "./shopAdminContract";

const SHOP = "/api/v1/shops/{shop_id}";
const MEMBER = `${SHOP}/members/{user_id}` as const;

export function createHttpShopAdmin({ api, session }: AppServices): ShopAdminGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const member = (shopId: string, userId: string) => ({ shop_id: shopId, user_id: userId });
  return {
    profile: (shopId) =>
      session.authorized((token) => api.get(`${SHOP}/profile`, { token, params: shop(shopId) })),
    members: (shopId) =>
      session.authorized((token) => api.get(`${SHOP}/members`, { token, params: shop(shopId) })),
    addMember: (shopId, body) =>
      session.authorized((token) =>
        api.post(`${SHOP}/members`, { token, params: shop(shopId), body }),
      ),
    updateMember: (shopId, userId, patch) =>
      session.authorized((token) =>
        api.patch(MEMBER, { token, params: member(shopId, userId), body: patch }),
      ),
    resetPin: async (shopId, userId) => {
      const reply = await session.authorized((token) =>
        api.post(`${MEMBER}/reset-pin`, { token, params: member(shopId, userId) }),
      );
      return reply.temporary_pin;
    },
    revokeDevices: async (shopId, userId) => {
      const reply = await session.authorized((token) =>
        api.post(`${MEMBER}/revoke-devices`, { token, params: member(shopId, userId) }),
      );
      return reply.revoked_sessions;
    },
    unlock: async (shopId, userId) => {
      await session.authorized((token) =>
        api.post(`${MEMBER}/unlock`, { token, params: member(shopId, userId) }),
      );
    },
    locations: async (shopId) => {
      const found = await session.authorized((token) =>
        api.get(`${SHOP}/locations`, { token, params: shop(shopId) }),
      );
      return found.items;
    },
    createLocation: (shopId, body) =>
      session.authorized((token) =>
        api.post(`${SHOP}/locations`, { token, params: shop(shopId), body }),
      ),
    updateLocation: (shopId, locationId, patch) =>
      session.authorized((token) =>
        api.patch(`${SHOP}/locations/{location_id}`, {
          token,
          params: { shop_id: shopId, location_id: locationId },
          body: patch,
        }),
      ),
    paymentModes: (shopId) =>
      session.authorized((token) =>
        api.get(`${SHOP}/payment-modes`, { token, params: shop(shopId) }),
      ),
    createPaymentMode: (shopId, body) =>
      session.authorized((token) =>
        api.post(`${SHOP}/payment-modes`, { token, params: shop(shopId), body }),
      ),
    updatePaymentMode: (shopId, modeId, patch) =>
      session.authorized((token) =>
        api.patch(`${SHOP}/payment-modes/{mode_id}`, {
          token,
          params: { shop_id: shopId, mode_id: modeId },
          body: patch,
        }),
      ),
    settings: (shopId) =>
      session.authorized((token) => api.get(`${SHOP}/settings`, { token, params: shop(shopId) })),
    updateSettings: (shopId, patch) =>
      session.authorized((token) =>
        api.patch(`${SHOP}/settings`, { token, params: shop(shopId), body: patch }),
      ),
  };
}

export const ShopAdminContext = createContext<ShopAdminGateway | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function useShopAdmin(): ShopAdminGateway {
  const gateway = useContext(ShopAdminContext);
  if (gateway === null) throw new Error("useShopAdmin doit être appelé sous ShopAdminContext");
  return gateway;
}
