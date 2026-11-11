/**
 * Gestion du catalogue (UC-STK-01 à 04, specs § 6.3) : alias **générés** de `schema.gen.ts`,
 * jamais réécrits. Les clés de prix et de coût de `ArticleResponse` sont absentes du JSON
 * quand le rôle ne les voit pas (TR-05) : l'écran ne lit l'article qu'à travers
 * `features/catalog/articleView.ts`, qui retire ce que le rôle ne doit pas voir.
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type ArticleResponse = Schemas["ArticleResponse"];
export type ArticleListResponse = Schemas["ArticleListResponse"];
export type ArticleCreateRequest = Schemas["ArticleCreateRequest"];
export type ArticlePatchRequest = Schemas["ArticlePatch"];
export type PricesRequest = Schemas["PricesRequest"];
export type PriceHistoryResponse = Schemas["PriceHistoryResponse"];
export type ProfileFieldResponse = Schemas["FieldResponse"];
export type FieldValue = Schemas["FieldValue"];

/** Filtre `?status=` de la liste (UC-STK-04 : archivés consultables). */
export type ArticleStatusFilter = "active" | "archived" | "all";

export interface ArticleListQuery {
  /** Texte tapé (dès la 1re lettre) ; vide = aucun filtre. */
  text: string;
  status: ArticleStatusFilter;
  /** Curseur opaque de la page suivante (`next_cursor`), `null` pour la première. */
  cursor: string | null;
  limit: number;
}

/** Ce que le formulaire d'article lit du profil (`GET /shops/{id}/profile`). */
export interface ArticleForm {
  fields: readonly ProfileFieldResponse[];
  /** Réglage « prix minimum » de la boutique (H9). */
  minPriceEnabled: boolean;
}

/**
 * Passerelle du catalogue. Erreurs : `ApiError` (`DUPLICATE`, `VERSION_CONFLICT`,
 * `MIN_PRICE_*`, `ARTICLE_HAS_STOCK`, `FORBIDDEN`…) ou `NetworkError` ; rien n'est avalé.
 */
export interface CatalogAdminGateway {
  articleForm(shopId: string): Promise<ArticleForm>;
  listArticles(shopId: string, query: ArticleListQuery): Promise<ArticleListResponse>;
  getArticle(shopId: string, articleId: string): Promise<ArticleResponse>;
  createArticle(shopId: string, body: ArticleCreateRequest): Promise<ArticleResponse>;
  updateArticle(
    shopId: string,
    articleId: string,
    body: ArticlePatchRequest,
  ): Promise<ArticleResponse>;
  setPrices(shopId: string, articleId: string, body: PricesRequest): Promise<ArticleResponse>;
  archiveArticle(shopId: string, articleId: string): Promise<ArticleResponse>;
  reactivateArticle(shopId: string, articleId: string): Promise<ArticleResponse>;
}
