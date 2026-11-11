/**
 * Adresses des écrans du catalogue, **dans** la section « Stock » (`/s/{shopId}/stock`) :
 * la fiche et la création sont des paramètres de recherche, si bien que l'entrée « Stock »
 * de la barre du bas reste allumée et que la coquille n'a qu'une route à connaître.
 *
 * - liste : `/s/{shopId}/stock`
 * - fiche : `/s/{shopId}/stock?article={id}`
 * - création : `/s/{shopId}/stock?article=nouveau`
 */
import { shopPath } from "../../core/profile/shopProfile";
import { STOCK_KEY } from "./catalogRights";

export const ARTICLE_PARAM = "article";
export const NEW_ARTICLE = "nouveau";

export function catalogListPath(shopId: string): string {
  return shopPath(shopId, STOCK_KEY);
}

export function articlePath(shopId: string, articleId: string): string {
  return `${catalogListPath(shopId)}?${ARTICLE_PARAM}=${encodeURIComponent(articleId)}`;
}

export function newArticlePath(shopId: string): string {
  return articlePath(shopId, NEW_ARTICLE);
}
