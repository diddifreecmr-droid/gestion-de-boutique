/**
 * Adresses des écrans du catalogue, **dans** la section « Stock » (`/s/{shopId}/stock`) :
 * la liste est l'onglet « Articles » de la section (l'onglet « Stock », sans paramètre, est la
 * matrice du module Stock), la fiche et la création sont des paramètres de recherche, si bien
 * que l'entrée « Stock » de la barre du bas reste allumée et que la coquille n'a qu'une route.
 *
 * - liste : `/s/{shopId}/stock?vue=articles`
 * - fiche : `/s/{shopId}/stock?article={id}`
 * - création : `/s/{shopId}/stock?article=nouveau`
 */
import { shopPath } from "../../core/profile/shopProfile";
import { STOCK_KEY } from "./catalogRights";

export const ARTICLE_PARAM = "article";
export const NEW_ARTICLE = "nouveau";
/** Paramètre de vue de la section « Stock » et valeur de l'onglet « Articles ». */
export const VIEW_PARAM = "vue";
export const ARTICLES_VIEW = "articles";

export function catalogListPath(shopId: string): string {
  return `${shopPath(shopId, STOCK_KEY)}?${VIEW_PARAM}=${ARTICLES_VIEW}`;
}

export function articlePath(shopId: string, articleId: string): string {
  return `${shopPath(shopId, STOCK_KEY)}?${ARTICLE_PARAM}=${encodeURIComponent(articleId)}`;
}

export function newArticlePath(shopId: string): string {
  return articlePath(shopId, NEW_ARTICLE);
}
