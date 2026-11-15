/**
 * Textes et tris des Coûts et marges (design-system § 7.2) : aucun calcul d'indicateur ici, le
 * serveur les donne tous (`GET /dashboard/margins`).
 */
import type { ArticleMargin, MarginFigures } from "../../../core/gateways/reportingContract";
import type { SortDirection } from "../../../shared/ui";
import { percentText } from "../periods";

/** « 26,67 % » ; sans chiffre d'affaires à coût connu : « non calculable ». */
export function rateText(figures: MarginFigures): string {
  return figures.margin_rate === null ? "non calculable" : percentText(figures.margin_rate);
}

/** « 2 ventes sans coût d'achat, hors marge » ; rien si toutes les lignes ont un coût. */
export function withoutCostText(figures: MarginFigures): string | null {
  const count = figures.without_cost;
  if (count === 0) return null;
  return `${String(count)} ligne${count > 1 ? "s" : ""} sans coût d'achat, hors marge`;
}

/** Les `count` articles à plus forte marge (le serveur les range déjà ainsi). */
export function bestArticles(articles: readonly ArticleMargin[], count = 3): ArticleMargin[] {
  return [...articles].sort((a, b) => b.figures.margin - a.figures.margin).slice(0, count);
}

export type SortValue = string | number | null;

/** Tri stable d'une ligne de tableau ; `null` (non calculable) toujours en dernier. */
export function sortRows<T>(
  rows: readonly T[],
  value: (row: T) => SortValue,
  direction: SortDirection,
): T[] {
  const sign = direction === "ascending" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const left = value(a);
    const right = value(b);
    if (left === null || right === null) return left === right ? 0 : left === null ? 1 : -1;
    if (typeof left === "number" && typeof right === "number") return sign * (left - right);
    return sign * String(left).localeCompare(String(right), "fr");
  });
}

/** Taux en nombre pour le tri (« 26.67 » → 26.67) ; `null` reste `null`. */
export function rateValue(figures: MarginFigures): number | null {
  return figures.margin_rate === null ? null : Number(figures.margin_rate);
}
