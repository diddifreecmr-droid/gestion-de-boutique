/** Lignes des listes qui expliquent un chiffre (UC-TDB-04), selon leur nature (`kind`). */
import type { DetailLine, DetailMetric } from "../../core/gateways/reportingContract";
import { shopPath } from "../../core/profile/shopProfile";
import { formatDate, formatMoney, formatQuantity } from "../../shared/format";
import { RECEIVABLES_KEY, VIEW as RECEIVABLE_VIEW } from "../receivables/receivablesNav";
import { SALES_KEY, saleLink } from "../sales/salesNav";
import { count } from "./homeText";

export const DETAIL_TITLES: Readonly<Record<DetailMetric, string>> = {
  sales: "Ventes de la période",
  payments: "Argent encaissé par mode de paiement",
  expenses: "Dépenses par catégorie",
  receivables: "Créances en cours",
  low_stock: "Stock bas",
};

export interface DetailRow {
  key: string;
  title: string;
  subtitle: string;
  amount?: number;
  /** Adresse de la fiche, si elle existe. */
  href?: string;
}

function need<T>(value: T | null | undefined, field: string, line: DetailLine): T {
  if (value === null || value === undefined) {
    throw new Error(`Ligne « ${line.kind} » ${line.id} sans ${field}`);
  }
  return value;
}

function marginText(margin: number | null | undefined): string {
  return margin === null || margin === undefined
    ? "Marge non calculable (coût inconnu)"
    : `Marge : ${formatMoney(margin)}`;
}

/** Nombre net d'une ligne : négatif quand les annulations de la période l'emportent. */
function netCount(value: number, one: string, many: string): string {
  return value < 0 ? count(-value, "annulation", "annulations") : count(value, one, many);
}

const SALE_WORDS: Readonly<Record<string, string>> = {
  sale: "Vente",
  cancellation: "Annulation de la vente",
  return: "Retour sur la vente",
};

export function detailRow(shopId: string, line: DetailLine): DetailRow {
  const key = `${line.kind}:${line.id}`;
  switch (line.kind) {
    case "sale":
    case "cancellation":
    case "return": {
      const day = formatDate(need(line.day, "date", line));
      return {
        key,
        title: `${SALE_WORDS[line.kind] ?? line.kind} ${line.label}`,
        subtitle: `${day} · ${marginText(line.margin)}`,
        amount: need(line.amount, "montant", line),
        // Un retour porte son propre identifiant, pas celui de la vente : pas de fiche.
        ...(line.kind === "return"
          ? {}
          : { href: shopPath(shopId, SALES_KEY) + saleLink(line.id) }),
      };
    }
    case "payment_mode":
      return {
        key,
        title: line.label,
        subtitle: netCount(need(line.count, "nombre", line), "paiement", "paiements"),
        amount: need(line.amount, "montant", line),
      };
    case "expense_category":
      return {
        key,
        title: line.label,
        subtitle: netCount(need(line.count, "nombre", line), "dépense", "dépenses"),
        amount: need(line.amount, "montant", line),
      };
    case "receivable":
      return {
        key,
        title: line.label,
        subtitle: `Depuis le ${formatDate(need(line.day, "date", line))}`,
        amount: need(line.amount, "montant", line),
        href: `${shopPath(shopId, RECEIVABLES_KEY)}?vue=${RECEIVABLE_VIEW.detail}&id=${encodeURIComponent(line.id)}`,
      };
    case "article":
      return {
        key,
        title: line.label,
        subtitle: `Stock : ${formatQuantity(need(line.quantity, "quantité", line))} · seuil : ${formatQuantity(need(line.threshold, "seuil", line))}`,
      };
    default:
      throw new Error(`Nature de ligne inconnue : « ${line.kind} »`);
  }
}

/** Total en tête de liste : montant, ou nombre d'articles pour le stock bas. */
export function totalText(metric: DetailMetric, total: number): string {
  return metric === "low_stock"
    ? count(total, "article sous le seuil", "articles sous le seuil")
    : formatMoney(total);
}
