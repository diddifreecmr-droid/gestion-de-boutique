/**
 * Passerelle **réelle** du catalogue : routes `/api/v1/shops/{shop_id}/articles…` (T13),
 * appelées avec le jeton de la session (rafraîchi puis rejoué au besoin).
 */
import type { AppServices } from "../services/createServices";
import type { CatalogAdminGateway } from "./catalogAdminContract";

const ARTICLES = "/api/v1/shops/{shop_id}/articles";
const ARTICLE = "/api/v1/shops/{shop_id}/articles/{article_id}";

export function createHttpCatalogAdmin({
  api,
  session,
  offline,
}: AppServices): CatalogAdminGateway {
  const ids = (shopId: string, articleId: string) => ({ shop_id: shopId, article_id: articleId });
  return {
    articleForm: async (shopId) => {
      const profile = await session.authorized((token) =>
        api.get("/api/v1/shops/{shop_id}/profile", { token, params: { shop_id: shopId } }),
      );
      offline.rights.note(shopId, profile.entitlements); // droit hors connexion (T23, TR-26)
      return { fields: profile.article_fields, minPriceEnabled: profile.min_price_enabled };
    },
    listArticles: (shopId, { text, status, cursor, limit }) => {
      const q = text.trim();
      return session.authorized((token) =>
        api.get(ARTICLES, {
          token,
          params: { shop_id: shopId },
          query: { q: q === "" ? null : q, status, cursor, limit },
        }),
      );
    },
    getArticle: (shopId, articleId) =>
      session.authorized((token) => api.get(ARTICLE, { token, params: ids(shopId, articleId) })),
    createArticle: (shopId, body) =>
      session.authorized((token) =>
        api.post(ARTICLES, { token, params: { shop_id: shopId }, body }),
      ),
    updateArticle: (shopId, articleId, body) =>
      session.authorized((token) =>
        api.patch(ARTICLE, { token, params: ids(shopId, articleId), body }),
      ),
    setPrices: (shopId, articleId, body) =>
      session.authorized((token) =>
        api.put("/api/v1/shops/{shop_id}/articles/{article_id}/prices", {
          token,
          params: ids(shopId, articleId),
          body,
        }),
      ),
    archiveArticle: (shopId, articleId) =>
      session.authorized((token) =>
        api.post("/api/v1/shops/{shop_id}/articles/{article_id}/archive", {
          token,
          params: ids(shopId, articleId),
        }),
      ),
    reactivateArticle: (shopId, articleId) =>
      session.authorized((token) =>
        api.post("/api/v1/shops/{shop_id}/articles/{article_id}/reactivate", {
          token,
          params: ids(shopId, articleId),
        }),
      ),
  };
}
