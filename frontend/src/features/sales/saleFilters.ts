/** Filtres de la liste des ventes (UC-VEN-05) : période, mode, comptant/crédit, vendeur. */
import type { SaleFilters, SaleKind } from "../../core/gateways/salesContract";
import { addDays, monthStart } from "../expenses/businessDay";
import type { Period } from "../expenses/filters";

/** Mêmes périodes que les dépenses : un seul sélecteur (`PeriodBar`) pour les deux listes. */
export type { Period };

/** Valeur « tous » des choix exclusifs. */
export const ALL = "tous";

export interface ListFilters {
  period: Period;
  from: string;
  to: string;
  kind: SaleKind | typeof ALL;
  modeId: string;
  sellerId: string;
  /** N° de vente ou châssis : cherché sur toutes les dates. */
  text: string;
}

export function defaultFilters(today: string): ListFilters {
  return {
    period: "today",
    from: today,
    to: today,
    kind: ALL,
    modeId: ALL,
    sellerId: ALL,
    text: "",
  };
}

export function periodProblem(filters: ListFilters): string | undefined {
  if (filters.text.trim() !== "" || filters.period !== "custom") return undefined;
  if (filters.from === "" || filters.to === "") return "Choisissez les deux dates";
  if (filters.from > filters.to) return "La date de début est après la date de fin";
  return undefined;
}

/** Filtres actifs (hors période et recherche), lus dans « Filtres (n) » : type, mode, vendeur. */
export function activeSaleFilters(filters: ListFilters): number {
  return [filters.kind !== ALL, filters.modeId !== ALL, filters.sellerId !== ALL].filter(Boolean)
    .length;
}

/** Requête de `GET /sales` ; une recherche (`q`) ignore la période (toutes dates). */
export function toQuery(filters: ListFilters, today: string): SaleFilters {
  const query: SaleFilters = {};
  const text = filters.text.trim();
  if (text !== "") query.q = text;
  else if (filters.period === "week") {
    query.from = addDays(today, -6);
    query.to = today;
  } else if (filters.period === "month") {
    query.from = monthStart(today);
    query.to = today;
  } else if (filters.period === "custom") {
    query.from = filters.from;
    query.to = filters.to;
  }
  if (filters.kind !== ALL) query.kind = filters.kind;
  if (filters.modeId !== ALL) query.payment_mode_id = filters.modeId;
  if (filters.sellerId !== ALL) query.seller_id = filters.sellerId;
  return query;
}
