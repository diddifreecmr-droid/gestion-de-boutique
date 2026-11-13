/** Filtres de la liste (UC-DEP-03) : période, catégorie, tag, lieu, auteur, mode. */
import type { ExpenseFilters } from "../../core/gateways/expensesContract";
import { addDays, monthStart } from "./businessDay";

export type Period = "today" | "week" | "month" | "custom";

export const PERIOD_LABELS: Readonly<Record<Period, string>> = {
  today: "Aujourd'hui",
  week: "7 derniers jours",
  month: "Ce mois-ci",
  custom: "Autres dates",
};

/** Valeur « tous » des choix exclusifs. */
export const ALL = "tous";

export interface ListFilters {
  period: Period;
  from: string;
  to: string;
  categoryId: string;
  tag: { id: string; name: string } | null;
  locationId: string;
  userId: string;
  modeId: string;
}

export function defaultFilters(today: string): ListFilters {
  return {
    period: "today",
    from: today,
    to: today,
    categoryId: ALL,
    tag: null,
    locationId: ALL,
    userId: ALL,
    modeId: ALL,
  };
}

/** Requête de `GET /expenses` ; « Aujourd'hui » = aucune date (journée métier du serveur). */
export function toQuery(filters: ListFilters, today: string): ExpenseFilters {
  const query: ExpenseFilters = {};
  if (filters.period === "week") {
    query.from = addDays(today, -6);
    query.to = today;
  } else if (filters.period === "month") {
    query.from = monthStart(today);
    query.to = today;
  } else if (filters.period === "custom") {
    if (filters.from === "" || filters.to === "") throw new Error("Période incomplète");
    query.from = filters.from;
    query.to = filters.to;
  }
  if (filters.categoryId !== ALL) query.category_id = filters.categoryId;
  if (filters.tag !== null) query.tag_id = filters.tag.id;
  if (filters.locationId !== ALL) query.location_id = filters.locationId;
  if (filters.userId !== ALL) query.user_id = filters.userId;
  if (filters.modeId !== ALL) query.payment_mode_id = filters.modeId;
  return query;
}

/** Période personnalisée lisible ? (dates présentes et dans l'ordre) */
export function periodProblem(filters: ListFilters): string | undefined {
  if (filters.period !== "custom") return undefined;
  if (filters.from === "" || filters.to === "") return "Choisissez les deux dates";
  if (filters.from > filters.to) return "La date de début est après la date de fin";
  return undefined;
}

/** Filtres actifs (hors période), lus dans « Filtres (n) » : catégorie, tag, lieu, auteur, mode. */
export function activeExpenseFilters(value: ListFilters): number {
  return [
    value.categoryId !== ALL,
    value.tag !== null,
    value.locationId !== ALL,
    value.userId !== ALL,
    value.modeId !== ALL,
  ].filter(Boolean).length;
}
