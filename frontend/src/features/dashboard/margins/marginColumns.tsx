/** Colonnes des tableaux de Coûts et marges (grand écran) : par article, par tissu, par jour. */
import type {
  ArticleMargin,
  DayMargin,
  FabricMargin,
  PerUnit,
} from "../../../core/gateways/reportingContract";
import { formatDate, formatMoney, formatQuantity } from "../../../shared/format";
import { rateText, rateValue } from "./marginText";
import type { Column } from "./SortableTable";

type Row = ArticleMargin | FabricMargin;

const money = (amount: number | null) => (amount === null ? "—" : formatMoney(amount));

function common<T extends Row>(): Column<T>[] {
  return [
    {
      key: "revenue",
      label: "Ventes",
      numeric: true,
      value: (r) => r.figures.revenue,
      render: (r) => money(r.figures.revenue),
    },
    {
      key: "cost",
      label: "Coût",
      numeric: true,
      value: (r) => r.figures.cost,
      render: (r) => money(r.figures.cost),
    },
    {
      key: "margin",
      label: "Marge",
      numeric: true,
      value: (r) => r.figures.margin,
      render: (r) => money(r.figures.margin),
    },
    {
      key: "rate",
      label: "Taux",
      numeric: true,
      value: (r) => rateValue(r.figures),
      render: (r) => rateText(r.figures),
    },
  ];
}

function perUnit<T extends Row>(unit: "per_meter" | "per_roll", label: string): Column<T>[] {
  const of = (r: T): PerUnit | null => r[unit];
  return [
    {
      key: `${unit}_cost`,
      label: `Coût ${label}`,
      numeric: true,
      value: (r) => of(r)?.cost ?? null,
      render: (r) => money(of(r)?.cost ?? null),
    },
    {
      key: `${unit}_margin`,
      label: `Marge ${label}`,
      numeric: true,
      value: (r) => of(r)?.margin ?? null,
      render: (r) => money(of(r)?.margin ?? null),
    },
  ];
}

function textileColumns<T extends Row>(textile: boolean): Column<T>[] {
  return textile
    ? [...perUnit<T>("per_meter", "au mètre"), ...perUnit<T>("per_roll", "au rouleau")]
    : [];
}

const quantity = (r: Row) =>
  formatQuantity(r.quantity, "stock_unit" in r && r.stock_unit !== "METER" ? undefined : "m");

export function articleColumns(textile: boolean): Column<ArticleMargin>[] {
  return [
    { key: "name", label: "Article", value: (r) => r.name, render: (r) => r.name },
    {
      key: "quantity",
      label: "Vendu",
      numeric: true,
      value: (r) => Number(r.quantity),
      render: quantity,
    },
    ...common<ArticleMargin>(),
    ...textileColumns<ArticleMargin>(textile),
  ];
}

export function fabricColumns(): Column<FabricMargin>[] {
  return [
    { key: "fabric", label: "Tissu", value: (r) => r.fabric, render: (r) => r.fabric },
    {
      key: "colors",
      label: "Couleurs",
      numeric: true,
      value: (r) => r.colors,
      render: (r) => String(r.colors),
    },
    {
      key: "quantity",
      label: "Vendu",
      numeric: true,
      value: (r) => Number(r.quantity),
      render: quantity,
    },
    ...common<FabricMargin>(),
    ...textileColumns<FabricMargin>(true),
  ];
}

export function dayColumns(): Column<DayMargin>[] {
  return [
    { key: "day", label: "Jour", value: (d) => d.day, render: (d) => formatDate(d.day) },
    {
      key: "revenue",
      label: "Ventes",
      numeric: true,
      value: (d) => d.revenue,
      render: (d) => money(d.revenue),
    },
    {
      key: "cost",
      label: "Coût",
      numeric: true,
      value: (d) => d.cost,
      render: (d) => money(d.cost),
    },
    {
      key: "margin",
      label: "Marge",
      numeric: true,
      value: (d) => d.margin,
      render: (d) => money(d.margin),
    },
  ];
}
