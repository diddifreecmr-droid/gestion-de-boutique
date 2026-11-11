/** Filtres de la liste des créances (UC-CRE-04) et leur traduction en paramètres d'API. */
import type {
  ReceivableFilters,
  ReceivableStatus,
  SeniorityBand,
} from "../../core/gateways/receivablesContract";

/** Valeur « aucun filtre » des choix exclusifs. */
export const ALL = "all";

export type FollowUp = typeof ALL | "reminder_overdue" | "quiet";

export interface ListFilters {
  status: ReceivableStatus | typeof ALL;
  sellerId: string;
  band: SeniorityBand | typeof ALL;
  followUp: FollowUp;
}

export const DEFAULT_FILTERS: ListFilters = {
  status: ALL,
  sellerId: ALL,
  band: ALL,
  followUp: ALL,
};

export function toQuery(filters: ListFilters): ReceivableFilters {
  const query: ReceivableFilters = {};
  if (filters.status !== ALL) query.status = filters.status;
  if (filters.sellerId !== ALL) query.seller_id = filters.sellerId;
  if (filters.band !== ALL) query.band = filters.band;
  if (filters.followUp === "reminder_overdue") query.reminder_overdue = true;
  if (filters.followUp === "quiet") query.quiet = true;
  return query;
}
