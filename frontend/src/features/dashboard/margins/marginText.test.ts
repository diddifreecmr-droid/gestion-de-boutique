import { describe, expect, it } from "vitest";
import { ARTICLES } from "../../../testing/margins";
import { bestArticles, rateText, sortRows, withoutCostText } from "./marginText";

describe("textes et tris des Coûts et marges", () => {
  it("taux, lignes sans coût et meilleurs articles", () => {
    const figures = { revenue: 0, cost: 0, margin: 0, margin_rate: null, without_cost: 2 };
    expect(rateText(figures)).toBe("non calculable");
    expect(withoutCostText(figures)).toBe("2 lignes sans coût d'achat, hors marge");
    expect(withoutCostText({ ...figures, without_cost: 0 })).toBeNull();
    expect(bestArticles(ARTICLES).map((a) => a.article_id)).toEqual(["a3", "a1", "a2"]);
  });

  it("tri stable, non calculable toujours en dernier", () => {
    const rows = [{ v: 2 }, { v: null }, { v: 5 }, { v: 1 }];
    const by = (row: { v: number | null }) => row.v;
    expect(sortRows(rows, by, "ascending").map(by)).toEqual([1, 2, 5, null]);
    expect(sortRows(rows, by, "descending").map(by)).toEqual([5, 2, 1, null]);
  });
});
