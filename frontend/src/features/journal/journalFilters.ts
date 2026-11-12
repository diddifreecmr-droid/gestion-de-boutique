/** Filtres du journal (UC-JRN-01 : période, utilisateur, type d'action, module). */
import type { AuditAction, JournalQuery } from "../../core/gateways/journalContract";

/** « Tous » : aucun filtre (valeur sentinelle des puces). */
export const ALL = "all";

export interface JournalFilters {
  from: string;
  to: string;
  userId: string;
  action: AuditAction | typeof ALL;
  module: string;
}

export const NO_FILTERS: JournalFilters = {
  from: "",
  to: "",
  userId: ALL,
  action: ALL,
  module: ALL,
};

/** Message si la période est incohérente, sinon `undefined`. */
export function periodProblem(filters: JournalFilters): string | undefined {
  if (filters.from !== "" && filters.to !== "" && filters.from > filters.to) {
    return "La date de fin doit suivre la date de début";
  }
  return undefined;
}

/** Requête de l'API (sans curseur) ; lève si la période est incohérente (fail-fast). */
export function toQuery(filters: JournalFilters): Omit<JournalQuery, "cursor"> {
  const problem = periodProblem(filters);
  if (problem !== undefined) throw new Error(problem);
  return {
    from: filters.from === "" ? null : filters.from,
    to: filters.to === "" ? null : filters.to,
    userId: filters.userId === ALL ? null : filters.userId,
    action: filters.action === ALL ? null : filters.action,
    module: filters.module === ALL ? null : filters.module,
  };
}

/** Clé de relecture : change dès qu'un filtre change. */
export function filtersKey(filters: JournalFilters): string {
  return [filters.from, filters.to, filters.userId, filters.action, filters.module].join("|");
}
