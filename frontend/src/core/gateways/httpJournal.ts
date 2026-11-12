/**
 * Passerelle réelle du Journal : `GET /api/v1/shops/{shop_id}/audit` et `/members` (T09, T10).
 * Rien n'est avalé : `ApiError` et `NetworkError` remontent à l'écran.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { JournalGateway } from "./journalContract";

const SHOP = "/api/v1/shops/{shop_id}";

export function createHttpJournal({ api, session }: AppServices): JournalGateway {
  return {
    list: (shopId, { from, to, userId, action, module, cursor }) =>
      session.authorized((token) =>
        api.get(`${SHOP}/audit`, {
          token,
          params: { shop_id: shopId },
          query: { from, to, user_id: userId, action, module, cursor },
        }),
      ),
    members: (shopId) =>
      session.authorized((token) =>
        api.get(`${SHOP}/members`, { token, params: { shop_id: shopId } }),
      ),
  };
}

export const JournalContext = createContext<JournalGateway | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function useJournalGateway(): JournalGateway {
  const gateway = useContext(JournalContext);
  if (gateway === null) throw new Error("useJournalGateway doit être appelé sous JournalContext");
  return gateway;
}
