import type { Purchase } from "../../core/gateways/purchasingContract";
import { usePurchasingDeps } from "../../core/gateways/httpPurchasing";
import { useLoad, type Loaded } from "../expenses/useLoad";
import { draftArticle, type DraftArticle } from "./draft";

export interface LoadedPurchase {
  purchase: Purchase;
  /** Nom et unité de chaque article de l'achat (la réponse ne porte que l'identifiant). */
  articles: ReadonlyMap<string, DraftArticle>;
}

/** Lit un achat puis ses articles (`GET /articles/{id}`, archivés compris) ; `round` relit. */
export function usePurchase(shopId: string, id: string, round = 0): Loaded<LoadedPurchase> {
  const { gateway, catalog } = usePurchasingDeps();
  return useLoad(`${shopId}:${id}:${String(round)}`, async () => {
    const purchase = await gateway.get(shopId, id);
    const ids = [...new Set(purchase.lines.map((line) => line.article_id))];
    const found = await Promise.all(ids.map((articleId) => catalog.getArticle(shopId, articleId)));
    return { purchase, articles: new Map(found.map((a) => [a.id, draftArticle(a)])) };
  });
}

/** Nom d'un article de l'achat ; absent = lecture incomplète (fail-fast). */
export function articleName(articles: ReadonlyMap<string, DraftArticle>, id: string): string {
  const found = articles.get(id);
  if (found === undefined) throw new Error(`Article de l'achat non chargé : « ${id} »`);
  return found.name;
}
