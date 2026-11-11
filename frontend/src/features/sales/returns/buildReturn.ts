/** Saisie → corps exact de `POST /sales/{id}/returns` (UC-VEN-09, T16b). */
import type { SaleReturnCommand, SaleReturns } from "../../../core/gateways/returnsContract";
import type { RecordSaleCommand, SaleResult } from "../../../core/gateways/salesContract";
import { buildCommand } from "../buildCommand";
import { needsChassis, type ReturnChecks, type ReturnDraft } from "./returnDraft";

/**
 * Nouvelle vente de l'échange : les lignes de « Nouvelle vente », au comptant, au lieu de la
 * vente d'origine, pour le même client et le même vendeur. Le serveur y verse l'avoir ; le
 * client ne paie que la différence (`payments`).
 */
function exchangeSale(
  sale: SaleResult,
  draft: ReturnDraft,
  checks: ReturnChecks,
  modeId: string,
  now: Date,
): RecordSaleCommand {
  const command = buildCommand(
    { ...draft.exchange, payment: modeId, split: null, cashGiven: null },
    sale.location_id,
    checks.exchange.total,
    now,
  );
  const { toPay } = checks.balance;
  return {
    ...command,
    customer: sale.customer_id === null ? null : { id: sale.customer_id, kind: "individual" },
    seller_id: sale.seller_id,
    payments: toPay > 0 ? [{ mode_id: modeId, amount: toPay, reference: null }] : [],
  };
}

export function buildReturn(
  sale: SaleResult,
  listing: SaleReturns,
  draft: ReturnDraft,
  checks: ReturnChecks,
  now: Date = new Date(),
): SaleReturnCommand {
  if (checks.blocking) throw new Error("buildReturn : saisie incomplète (contrôle sauté ?)");
  const lines = Object.entries(draft.picks)
    .map(([position, pick]) => ({ line: Number(position), pick }))
    .filter(({ pick }) => pick.quantity > 0)
    .sort((a, b) => a.line - b.line)
    .map(({ line, pick }) => ({
      line,
      quantity: String(pick.quantity),
      condition: pick.condition,
      chassis: needsChassis(sale, listing, line, pick) ? pick.chassis : [],
    }));
  const base = { id: draft.id, lines, reason: draft.reason.trim() };
  if (draft.kind === "exchange") {
    if (draft.modeId === null) throw new Error("buildReturn : mode de l'échange absent");
    const exchange = {
      sale: exchangeSale(sale, draft, checks, draft.modeId, now),
      mode_id: draft.modeId,
    };
    return { ...base, refund: null, exchange };
  }
  const amount = draft.refundAmount ?? 0;
  if (amount === 0) return { ...base, refund: null, exchange: null };
  if (draft.modeId === null) throw new Error("buildReturn : mode du remboursement absent");
  return {
    ...base,
    refund: { amount, mode_id: draft.modeId, refunded_on: draft.refundOn },
    exchange: null,
  };
}
