/** Libellés des codes stables du module Créances (CDC § 10.1, UC-CRE-04, UC-CRE-06). */
import type { BadgeStatus } from "../../shared/ui";
import type { ReceivableStatus, SeniorityBand } from "../../core/gateways/receivablesContract";

function lookup<T extends string, V>(table: Readonly<Record<T, V>>, code: string, what: string): V {
  if (!Object.hasOwn(table, code)) throw new Error(`${what} inconnu reçu de l'API : « ${code} »`);
  return table[code as T];
}

/** Statut d'une créance : mot + couleur de pastille (design-system § 6.4). */
const STATUSES: Readonly<Record<ReceivableStatus, { label: string; badge: BadgeStatus }>> = {
  open: { label: "En cours", badge: "credit" },
  settled: { label: "Soldée", badge: "success" },
  cancelled: { label: "Annulée", badge: "danger" },
  written_off: { label: "En perte", badge: "danger" },
};

export const STATUS_CODES = Object.keys(STATUSES) as ReceivableStatus[];

export const statusOf = (code: string) => lookup(STATUSES, code, "Statut de créance");

const BANDS: Readonly<Record<SeniorityBand, string>> = {
  under_30: "Moins de 30 jours",
  "31_60": "31 à 60 jours",
  "61_90": "61 à 90 jours",
  over_90: "Plus de 90 jours",
};

export const BAND_CODES = Object.keys(BANDS) as SeniorityBand[];

export const bandLabel = (code: string) => lookup(BANDS, code, "Classe d'ancienneté");

const REMINDERS: Readonly<Record<string, { label: string; badge: BadgeStatus }>> = {
  upcoming: { label: "À venir", badge: "warning" },
  done: { label: "Fait", badge: "success" },
  postponed: { label: "Reporté", badge: "warning" },
};

export const reminderStatus = (code: string) => lookup(REMINDERS, code, "Statut de rappel");

/** Opérations du relevé client (UC-CRE-05). */
const KINDS: Readonly<Record<string, string>> = {
  sale: "Vente à crédit",
  deposit: "Acompte",
  opening: "Créance ancienne",
  installment: "Versement",
  write_off: "Mise en perte",
  cancellation: "Vente annulée",
};

export const statementKind = (code: string) => lookup(KINDS, code, "Opération de relevé");

/** « 1 jour », « 45 jours ». */
export const daysText = (days: number) =>
  days <= 1 ? `${String(days)} jour` : `${String(days)} jours`;
