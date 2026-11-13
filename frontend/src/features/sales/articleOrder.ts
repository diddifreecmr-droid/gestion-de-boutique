/** Ordre des articles proposés à la vente (audit UX du 13/11/2026). */
import type { CatalogArticle } from "../../core/gateways/catalogContract";
import { unitStock } from "./draft";

/** Vendable ici : vente à l'unité et au moins une unité au lieu de vente. */
export function sellable(article: CatalogArticle): boolean {
  return article.sale_mode === "unit" && unitStock(article) >= 1;
}

/**
 * Les articles vendables d'abord, dans l'ordre du serveur (plus vendus) ; les ruptures et
 * articles non vendables ensuite, toujours visibles et marqués (« Rupture »).
 */
export function sellableFirst(items: readonly CatalogArticle[]): CatalogArticle[] {
  return [...items.filter(sellable), ...items.filter((article) => !sellable(article))];
}
