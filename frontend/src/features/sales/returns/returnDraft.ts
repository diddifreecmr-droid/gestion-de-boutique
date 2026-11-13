/**
 * Saisie d'un retour ou d'un échange (UC-VEN-09), telle que l'écran la tient, et ses contrôles.
 * Le brouillon n'est jamais effacé par un échec d'envoi.
 */
import { uuidV7 } from "../../../core/api/uuidv7";
import type { Role } from "../../../core/auth/me";
import type { SaleReturns, StockCondition } from "../../../core/gateways/returnsContract";
import type { SaleResult } from "../../../core/gateways/salesContract";
import { formatMoney } from "../../../shared/format";
import { businessDay } from "../buildCommand";
import { newDraft, type SaleDraft } from "../draft";
import { checkSale, type SaleChecks } from "../saleChecks";
import {
  exchangeBalance,
  returnValue,
  returnableOf,
  settlement,
  type ExchangeBalance,
  type Settlement,
} from "./returnMath";

export type ReturnKind = "refund" | "exchange";
/** Nouvelle vente de l'échange : comptant, ou à crédit pour le client d'origine. */
export type ExchangeKind = "cash" | "credit";

export interface LinePick {
  quantity: number;
  condition: StockCondition;
  /** Châssis rendus (texte tel que vendu), à préciser sur une ligne rendue en partie. */
  chassis: string[];
}

export interface ReturnDraft {
  /** UUIDv7 du retour : le même à chaque renvoi (idempotence). */
  id: string;
  kind: ReturnKind;
  /** Par position de ligne (1 = première). */
  picks: Record<number, LinePick>;
  reason: string;
  refundAmount: number | null;
  /** Mode du remboursement, ou de l'avoir et de la différence d'un échange. */
  modeId: string | null;
  refundOn: string;
  /** Nouvelle vente de l'échange (mêmes lignes et contrôles que « Nouvelle vente »). */
  exchange: SaleDraft;
  exchangeKind: ExchangeKind;
  /** Acompte d'un échange à crédit, versé dans le mode de l'échange. */
  deposit: number | null;
}

export function newReturnDraft(modeId: string | null, now: Date = new Date()): ReturnDraft {
  return {
    id: uuidV7(),
    kind: "refund",
    picks: {},
    reason: "",
    refundAmount: null,
    modeId,
    refundOn: businessDay(now),
    exchange: newDraft(modeId),
    exchangeKind: "cash",
    deposit: null,
  };
}

/** Clé normalisée d'un châssis (lettres et chiffres en majuscules, comme le serveur). */
export function chassisKey(text: string): string {
  return text.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

/** Châssis d'une ligne encore à rendre (vendus moins ceux des retours précédents). */
export function chassisLeft(sale: SaleResult, listing: SaleReturns, line: number): string[] {
  const done = new Set(
    listing.returns
      .flatMap((made) => made.lines)
      .filter((l) => l.line === line)
      .flatMap((l) => l.chassis.map(chassisKey)),
  );
  return (sale.lines[line - 1]?.details ?? [])
    .map((detail) => detail.chassis_number)
    .filter((text): text is string => text !== null && text !== "" && !done.has(chassisKey(text)));
}

/** La ligne est rendue en partie et porte des châssis : il faut dire lesquels. */
export function needsChassis(sale: SaleResult, listing: SaleReturns, line: number, pick: LinePick) {
  const partial = pick.quantity < returnableOf(listing, line);
  return pick.quantity > 0 && partial && chassisLeft(sale, listing, line).length > 0;
}

export interface ReturnChecks {
  value: number;
  settlement: Settlement;
  exchange: SaleChecks;
  balance: ExchangeBalance;
  lines?: string;
  chassis: Record<number, string>;
  reason?: string;
  refund?: string;
  mode?: string;
  refundOn?: string;
  exchangeLines?: string;
  /** Échange à crédit impossible (vente d'origine sans client, rien à payer). */
  credit?: string;
  deposit?: string;
  /** Reste dû d'un échange à crédit (la créance), 0 au comptant. */
  creditDue: number;
  blocking: boolean;
}

function checkCredit(sale: SaleResult, draft: ReturnDraft, checks: ReturnChecks): void {
  const { toPay } = checks.balance;
  const deposit = draft.deposit ?? 0;
  if (sale.customer_id === null) {
    checks.credit = "La vente d'origine n'a pas de client : l'échange à crédit est impossible";
  } else if (toPay === 0 && draft.exchange.lines.length > 0) {
    checks.credit = "L'avoir couvre la nouvelle vente : choisissez « Comptant »";
  }
  if (toPay > 0 && deposit >= toPay) {
    checks.deposit = `L'acompte doit rester inférieur à ${formatMoney(toPay)} (sinon « Comptant »)`;
  }
  checks.creditDue = Math.max(0, toPay - deposit);
}

export function checkReturn(
  sale: SaleResult,
  listing: SaleReturns,
  draft: ReturnDraft,
  role: Role = "owner",
) {
  const value = returnValue(sale, listing, draft.picks);
  const settled = settlement(sale, listing, value);
  // Employé : sous le minimum, l'avertissement du Lot 1 (vente acceptée, journal).
  const exchange = checkSale(draft.exchange, role, false);
  const checks: ReturnChecks = {
    value,
    settlement: settled,
    exchange,
    balance: exchangeBalance(settled.refundMax, exchange.total),
    chassis: {},
    creditDue: 0,
    blocking: false,
  };
  const chosen = Object.entries(draft.picks).filter(([, pick]) => pick.quantity > 0);
  if (chosen.length === 0) checks.lines = "Choisissez au moins un article rendu";
  chosen.forEach(([position, pick]) => {
    const line = Number(position);
    if (needsChassis(sale, listing, line, pick) && pick.chassis.length !== pick.quantity) {
      checks.chassis[line] = `Choisissez ${String(pick.quantity)} châssis rendu(s)`;
    }
  });
  if (draft.reason.trim() === "") checks.reason = "Le motif est obligatoire";
  const amount = draft.refundAmount ?? 0;
  if (draft.kind === "refund") {
    if (amount > settled.refundMax) {
      checks.refund = `Le remboursement ne peut pas dépasser ${formatMoney(settled.refundMax)}`;
    }
    if (amount > 0 && draft.modeId === null) checks.mode = "Choisissez le mode du remboursement";
    const today = businessDay();
    if (amount > 0 && (draft.refundOn > today || draft.refundOn < sale.sold_on)) {
      checks.refundOn = "La date va du jour de la vente à aujourd'hui";
    }
  } else {
    if (draft.exchange.lines.length === 0)
      checks.exchangeLines = "Ajoutez l'article remis au client";
    if (draft.modeId === null) checks.mode = "Choisissez le mode de paiement de la différence";
    if (draft.exchangeKind === "credit") checkCredit(sale, draft, checks);
  }
  const exchangeBlocking =
    draft.kind === "exchange" &&
    Object.values(exchange.lines).some(
      (issues) => issues.price !== undefined || issues.chassis.some((e) => e !== undefined),
    );
  checks.blocking =
    exchangeBlocking ||
    Object.keys(checks.chassis).length > 0 ||
    [
      checks.lines,
      checks.reason,
      checks.refund,
      checks.mode,
      checks.refundOn,
      checks.exchangeLines,
      checks.credit,
      checks.deposit,
    ].some((error) => error !== undefined);
  return checks;
}
