/**
 * Faux serveur des Coûts et marges (tests seulement) : réponses typées par le contrat généré.
 * Boutique Textile : tissu « Djampar » en deux couleurs (rouleau de 25 m) et une moto.
 */
import type {
  ArticleMargin,
  DayMargin,
  Margins,
  PerUnit,
} from "../core/gateways/reportingContract";
import { SHOP_A } from "./fakeApi";

export const MARGINS_TODAY = `GET /api/v1/shops/${SHOP_A}/dashboard/margins?period=today`;

const figures = (revenue: number, cost: number, rate: string | null, withoutCost = 0) => ({
  revenue,
  cost,
  margin: revenue - cost,
  margin_rate: rate,
  without_cost: withoutCost,
});

const unit = (price: number, cost: number): PerUnit => ({ price, cost, margin: price - cost });

function cloth(id: string, color: string, meters: string, revenue: number, cost: number) {
  return {
    article_id: id,
    name: `Djampar — ${color}`,
    fabric: "Djampar",
    stock_unit: "METER",
    quantity: meters,
    figures: figures(revenue, cost, ((100 * (revenue - cost)) / revenue).toFixed(2)),
    roll_length_m: "25",
    per_meter: unit(revenue / Number(meters), cost / Number(meters)),
    per_roll: unit((25 * revenue) / Number(meters), (25 * cost) / Number(meters)),
  } satisfies ArticleMargin;
}

export const ARTICLES: ArticleMargin[] = [
  cloth("a1", "Rouge", "30", 120_000, 90_000),
  cloth("a2", "Vert", "10", 50_000, 30_000),
  {
    article_id: "a3",
    name: "Haojue DR160",
    fabric: null,
    stock_unit: "UNIT",
    quantity: "1",
    figures: figures(800_000, 550_000, "31.25"),
    roll_length_m: null,
    per_meter: null,
    per_roll: null,
  },
  cloth("a4", "Bleu", "5", 20_000, 15_000),
];

const DAYS: DayMargin[] = [
  { day: "2026-11-10", revenue: 170_000, cost: 120_000, margin: 50_000 },
  { day: "2026-11-11", revenue: 820_000, cost: 565_000, margin: 255_000 },
];

export function marginsBody(overrides: Partial<Margins> = {}): Margins {
  return {
    period: { kind: "today", first_day: "2026-11-11", last_day: "2026-11-11", days: 1 },
    totals: figures(990_000, 685_000, "30.81", 1),
    articles: ARTICLES,
    fabrics: [
      {
        fabric: "Djampar",
        colors: 3,
        quantity: "45",
        figures: figures(190_000, 135_000, "28.95"),
        roll_length_m: "25",
        per_meter: unit(4_222, 3_000),
        per_roll: unit(105_556, 75_000),
      },
    ],
    days: DAYS,
    ...overrides,
  };
}
