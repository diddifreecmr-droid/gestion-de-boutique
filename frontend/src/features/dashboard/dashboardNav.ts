/**
 * Accueil du propriétaire : la période et le détail ouvert sont dans l'adresse
 * (`/s/{id}?periode=week`, `?periode=custom&du=…&au=…`, `&detail=sales`), si bien que le
 * bouton retour du téléphone revient de la liste au tableau de bord (UC-TDB-02, UC-TDB-04).
 * Module léger : l'accueil (`app/RoleHome`) l'importe sans charger l'écran.
 */
import { useSearchParams } from "react-router";
import type { DetailMetric, PeriodKind } from "../../core/gateways/reportingContract";

export const PERIOD_PARAM = "periode";
export const FROM_PARAM = "du";
export const TO_PARAM = "au";
export const DETAIL_PARAM = "detail";

export const PERIOD_KINDS: readonly PeriodKind[] = [
  "today",
  "yesterday",
  "week",
  "month",
  "last_month",
  "custom",
];

export const DETAIL_METRICS: readonly DetailMetric[] = [
  "sales",
  "payments",
  "expenses",
  "receivables",
  "low_stock",
];

/** Période choisie : `from` / `to` ne servent qu'à la période libre. */
export interface PeriodChoice {
  kind: PeriodKind;
  from: string;
  to: string;
}

function isPeriodKind(value: string): value is PeriodKind {
  return (PERIOD_KINDS as readonly string[]).includes(value);
}

function isMetric(value: string): value is DetailMetric {
  return (DETAIL_METRICS as readonly string[]).includes(value);
}

/** Période de l'adresse ; « Aujourd'hui » sans paramètre. Une valeur inconnue est refusée. */
export function readChoice(params: URLSearchParams): PeriodChoice {
  const kind = params.get(PERIOD_PARAM) ?? "today";
  if (!isPeriodKind(kind)) throw new Error(`Période inconnue dans l'adresse : « ${kind} »`);
  return { kind, from: params.get(FROM_PARAM) ?? "", to: params.get(TO_PARAM) ?? "" };
}

/** Indicateur détaillé dans l'adresse, ou `null` (le tableau de bord). */
export function readMetric(params: URLSearchParams): DetailMetric | null {
  const metric = params.get(DETAIL_PARAM);
  if (metric === null) return null;
  if (!isMetric(metric)) throw new Error(`Détail inconnu dans l'adresse : « ${metric} »`);
  return metric;
}

function choiceParams(choice: PeriodChoice): Record<string, string> {
  if (choice.kind === "today") return {};
  if (choice.kind !== "custom") return { [PERIOD_PARAM]: choice.kind };
  return { [PERIOD_PARAM]: choice.kind, [FROM_PARAM]: choice.from, [TO_PARAM]: choice.to };
}

export interface DashboardNav {
  choice: PeriodChoice;
  metric: DetailMetric | null;
  /** Nouvelle période ; la période libre part de `today` → `today`. */
  choose: (kind: PeriodKind, today: string) => void;
  range: (from: string, to: string) => void;
  open: (metric: DetailMetric) => void;
  /** Retour au tableau de bord, sur la même période. */
  close: () => void;
}

export function useDashboardNav(): DashboardNav {
  const [params, setParams] = useSearchParams();
  const choice = readChoice(params);
  const metric = readMetric(params);
  const go = (next: Record<string, string>, replace = false) => {
    setParams(next, { replace });
  };
  return {
    choice,
    metric,
    choose: (kind, today) => {
      go(choiceParams({ kind, from: today, to: today }), true);
    },
    range: (from, to) => {
      go(choiceParams({ kind: "custom", from, to }), true);
    },
    open: (next) => {
      go({ ...choiceParams(choice), [DETAIL_PARAM]: next });
    },
    close: () => {
      go(choiceParams(choice));
    },
  };
}
