/**
 * Qui peut échanger une vente, et jusqu'à quand (UC-PAP-01, décision client QC-4, T42). Le
 * serveur reste juge (403 réglage désactivé, 422 `EXCHANGE_PERIOD_OVER`) ; l'écran ne propose
 * que ce qui passera, et dit le délai.
 *
 * - Délai **inclusif** depuis la journée de la vente : vente du 13, délai 7 → jusqu'au 20 inclus.
 *   Délai absent = aucune limite.
 * - Propriétaire : toute vente, délai dépassable (confirmation « hors délai », journal sensible).
 * - Employé : seulement si le réglage `employee_exchange_allowed` est actif, sur **ses** ventes,
 *   dans le délai.
 */
import type { ExchangeRules } from "../../../core/profile/types";
import type { SaleResult } from "../../../core/gateways/salesContract";
import { businessDay } from "../buildCommand";
import type { SaleRole } from "../salesNav";

const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

/** « AAAA-MM-JJ » + `days` jours (calendrier, sans fuseau). */
export function addDays(day: string, days: number): string {
  const match = ISO_DAY.exec(day);
  if (match === null) throw new Error(`Date « ${day} » : format AAAA-MM-JJ attendu`);
  if (!Number.isInteger(days) || days < 0)
    throw new Error(`Délai d'échange invalide : ${String(days)}`);
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** « 20/11 » d'un jour « 2026-11-20 ». */
export function dayMonth(day: string): string {
  const match = ISO_DAY.exec(day);
  if (match === null) throw new Error(`Date « ${day} » : format AAAA-MM-JJ attendu`);
  return `${match[3] ?? ""}/${match[2] ?? ""}`;
}

export type ExchangeAccess =
  /** Aucun échange proposé (réglage désactivé, vente d'un autre, vente annulée). */
  | { kind: "none" }
  /** Échange proposé ; `deadline` null = sans limite ; `late` : propriétaire hors délai. */
  | { kind: "open"; deadline: string | null; late: boolean }
  /** Employé hors délai : il ne peut plus, seul le propriétaire le peut. */
  | { kind: "over"; deadline: string };

export interface ExchangeWho {
  role: SaleRole;
  userId: string;
}

export function exchangeAccess(
  sale: Pick<SaleResult, "status" | "sold_on" | "seller_id">,
  who: ExchangeWho,
  rules: ExchangeRules,
  today: string = businessDay(),
): ExchangeAccess {
  if (sale.status !== "valid") return { kind: "none" };
  if (who.role !== "owner" && (!rules.employeeAllowed || sale.seller_id !== who.userId)) {
    return { kind: "none" };
  }
  const deadline = rules.days === null ? null : addDays(sale.sold_on, rules.days);
  const late = deadline !== null && today > deadline;
  if (late && who.role !== "owner") return { kind: "over", deadline };
  return { kind: "open", deadline, late };
}

/** « Échange possible jusqu'au 20/11 » ; propriétaire hors délai : le délai passé. */
export function deadlineText(access: ExchangeAccess): string | null {
  if (access.kind === "over") {
    return `Délai d'échange dépassé (jusqu'au ${dayMonth(access.deadline)}) : seul le propriétaire peut encore échanger cette vente.`;
  }
  if (access.kind !== "open" || access.deadline === null) return null;
  return access.late
    ? `Délai d'échange dépassé (jusqu'au ${dayMonth(access.deadline)}) : un échange sera inscrit au journal.`
    : `Échange possible jusqu'au ${dayMonth(access.deadline)}`;
}

/** Texte de la confirmation du propriétaire hors délai (action sensible, journal). */
export const LATE_CONFIRM_TITLE = "Échange hors délai ?";
export const LATE_CONFIRM_TEXT =
  "Le délai d'échange de cette vente est dépassé. Vous pouvez l'échanger quand même : l'échange hors délai sera inscrit au journal.";
