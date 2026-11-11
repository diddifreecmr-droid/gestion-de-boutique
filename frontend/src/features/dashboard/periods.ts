/**
 * Périodes du tableau de bord (UC-TDB-02) : libellés, vérification de la période libre (mêmes
 * règles que `backend/app/application/reporting/periods.py`) et mots de la comparaison.
 */
import type { PeriodKind, PeriodOut, PeriodQuery } from "../../core/gateways/reportingContract";
import { formatDate, MINUS, NBSP } from "../../shared/format";
import { PERIOD_KINDS, type PeriodChoice } from "./dashboardNav";

/** Longueur maximale d'une période libre (`MAX_PERIOD_DAYS` du serveur). */
export const MAX_PERIOD_DAYS = 366;

export const PERIOD_LABELS: Readonly<Record<PeriodKind, string>> = {
  today: "Aujourd'hui",
  yesterday: "Hier",
  week: "Cette semaine",
  month: "Ce mois",
  last_month: "Mois dernier",
  custom: "Période libre",
};

const SUFFIX: Readonly<Record<PeriodKind, string>> = {
  today: "du jour",
  yesterday: "d'hier",
  week: "de la semaine",
  month: "du mois",
  last_month: "du mois dernier",
  custom: "de la période",
};

/** « Ventes du jour », « Marge de la semaine »… */
export function figureLabel(base: string, kind: PeriodKind): string {
  return `${base} ${SUFFIX[kind]}`;
}

function dayCount(from: string, to: string): number {
  const start = Date.parse(`${from}T00:00:00Z`);
  const end = Date.parse(`${to}T00:00:00Z`);
  if (Number.isNaN(start) || Number.isNaN(end)) throw new Error(`Dates invalides : ${from}, ${to}`);
  return Math.round((end - start) / 86_400_000) + 1;
}

/** Requête de la période, ou le message qui explique pourquoi elle n'est pas encore valable. */
export function resolveChoice(
  choice: PeriodChoice,
  today: string,
): { query: PeriodQuery } | { problem: string } {
  if (choice.kind !== "custom") return { query: { period: choice.kind } };
  const { from, to } = choice;
  if (from === "") return { problem: "Choisissez la date de début" };
  if (to === "") return { problem: "Choisissez la date de fin" };
  if (from > to) return { problem: "La date de début est après la date de fin" };
  if (to > today) return { problem: "La période ne peut pas finir après aujourd'hui" };
  if (dayCount(from, to) > MAX_PERIOD_DAYS) {
    return { problem: `Période trop longue : ${String(MAX_PERIOD_DAYS)} jours au plus` };
  }
  return { query: { period: "custom", from, to } };
}

/** Clé stable d'une requête (relecture quand la période change). */
export function queryKey(query: PeriodQuery): string {
  return query.period === "custom" ? `custom:${query.from}:${query.to}` : query.period;
}

/** Ce à quoi la période est comparée : « hier », « la veille », « la période précédente ». */
export function previousWord(period: PeriodOut): string {
  if (period.days > 1) return "la période précédente";
  if (period.kind === "today") return "hier";
  if (period.kind === "yesterday") return "avant-hier";
  return "la veille";
}

const PERCENT = /^-?\d+\.\d{2}$/;

/** Variation entière (« 28.57 » → 29, « -12.50 » → −13), `null` si non calculable. */
export function changePercent(value: string | null): number | null {
  if (value === null) return null;
  if (!PERCENT.test(value)) throw new Error(`Pourcentage illisible : « ${value} »`);
  const number = Number(value);
  return Math.sign(number) * Math.round(Math.abs(number));
}

/** « 26.07 » → « 26,07 % ». */
export function percentText(value: string): string {
  if (!PERCENT.test(value)) throw new Error(`Pourcentage illisible : « ${value} »`);
  return `${value.replace("-", MINUS).replace(".", ",")}${NBSP}%`;
}

/** « Le 11/11/2026 » ou « Du 01/11/2026 au 11/11/2026 ». */
export function periodText(period: PeriodOut): string {
  if (period.days === 1) return `Le ${formatDate(period.first_day)}`;
  return `Du ${formatDate(period.first_day)} au ${formatDate(period.last_day)}`;
}

/** Nature de la période renvoyée (chaîne libre dans le contrat) : une valeur inconnue est refusée. */
export function kindOf(period: PeriodOut): PeriodKind {
  const found = PERIOD_KINDS.find((kind) => kind === period.kind);
  if (found === undefined) throw new Error(`Période inconnue renvoyée : « ${period.kind} »`);
  return found;
}
