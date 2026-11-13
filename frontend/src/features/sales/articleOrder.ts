/** Ordre des articles proposés à la vente (audit UX du 13/11/2026). */
import type { CatalogArticle } from "../../core/gateways/catalogContract";
import { inStock } from "./draft";

/** Vendable ici : au moins une unité (ou 0,1 m pour un article au mètre) au lieu de vente. */
export function sellable(article: CatalogArticle): boolean {
  return inStock(article);
}

/**
 * Les articles vendables d'abord, dans l'ordre du serveur (plus vendus) ; les ruptures ensuite,
 * toujours visibles et marquées (« Rupture »).
 */
export function sellableFirst(items: readonly CatalogArticle[]): CatalogArticle[] {
  return [...items.filter(sellable), ...items.filter((article) => !sellable(article))];
}
