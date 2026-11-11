/** Filtres de la liste des achats (UC-ACH-05) : période, fournisseur, article, lieu. */
import type { PurchaseFilters } from "../../core/gateways/purchasingContract";
import { addDays } from "../expenses/businessDay";

export type Period = "month" | "week" | "today" | "custom";

export const PERIOD_LABELS: Readonly<Record<Period, string>> = {
  month: "Ce mois-ci",
  week: "7 derniers jours",
  today: "Aujourd'hui",
  custom: "Autres dates",
};

/** Valeur « tous » des choix exclusifs. */
export const ALL = "tous";

export interface ListFilters {
  period: Period;
  from: string;
  to: string;
  supplierId: string;
  locationId: string;
  article: { id: string; name: string } | null;
}

export function defaultFilters(today: string): ListFilters {
  return {
    period: "month",
    from: today,
    to: today,
    supplierId: ALL,
    locationId: ALL,
    article: null,
  };
}

/** Requête de `GET /purchases` ; « Ce mois-ci » = aucune date (mois en cours du serveur). */
export function toQuery(filters: ListFilters, today: string): PurchaseFilters {
  const query: PurchaseFilters = {};
  if (filters.period === "week") {
    query.from = addDays(today, -6);
    query.to = today;
  } else if (filters.period === "today") {
    query.from = today;
    query.to = today;
  } else if (filters.period === "custom") {
    if (filters.from === "" || filters.to === "") throw new Error("Période incomplète");
    query.from = filters.from;
    query.to = filters.to;
  }
  if (filters.supplierId !== ALL) query.supplier_id = filters.supplierId;
  if (filters.locationId !== ALL) query.location_id = filters.locationId;
  if (filters.article !== null) query.article_id = filters.article.id;
  return query;
}

/** Période personnalisée lisible ? (dates présentes et dans l'ordre) */
export function periodProblem(filters: ListFilters): string | undefined {
  if (filters.period !== "custom") return undefined;
  if (filters.from === "" || filters.to === "") return "Choisissez les deux dates";
  if (filters.from > filters.to) return "La date de début est après la date de fin";
  return undefined;
}
