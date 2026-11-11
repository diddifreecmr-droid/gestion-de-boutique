/**
 * Calculs indicatifs d'un retour (UC-VEN-09), mêmes règles que le serveur (T16b,
 * `return_lines.py`, `sale_return.settlement`) : le serveur reste juge, l'écran dit tout de
 * suite le plafond du remboursement, la baisse de la créance et la différence d'un échange.
 */
import type { SaleReturn, SaleReturns } from "../../../core/gateways/returnsContract";
import type { SaleResult } from "../../../core/gateways/salesContract";

export interface ReturnPick {
  /** Quantité rendue (0 = ligne non rendue). */
  quantity: number;
}

/** Déjà rendu sur une ligne (position 1 = première) : montant cumulé. */
function returnedAmount(returns: readonly SaleReturn[], line: number): number {
  return returns
    .flatMap((made) => made.lines)
    .filter((done) => done.line === line)
    .reduce((sum, done) => sum + done.amount, 0);
}

/** Encore rendable d'une ligne, en nombre (chaîne décimale de l'API). */
export function returnableOf(listing: SaleReturns, line: number): number {
  const balance = listing.balances.find((b) => b.line === line);
  if (balance === undefined) throw new Error(`Retour : ligne ${String(line)} sans solde`);
  return Number(balance.returnable);
}

/**
 * Valeur rendue : quantité × prix vendu, arrondie au franc ; le dernier retour d'une ligne
 * prend le reste exact (somme des retours = total de la ligne).
 */
export function returnValue(
  sale: SaleResult,
  listing: SaleReturns,
  picks: Readonly<Record<number, ReturnPick>>,
): number {
  return Object.entries(picks).reduce((sum, [position, pick]) => {
    if (pick.quantity <= 0) return sum;
    const line = Number(position);
    const sold = sale.lines[line - 1];
    if (sold === undefined) throw new Error(`Retour : ligne ${position} inconnue`);
    const full = pick.quantity === returnableOf(listing, line);
    const value = full
      ? sold.line_total - returnedAmount(listing.returns, line)
      : Math.round(pick.quantity * sold.unit_price);
    return sum + value;
  }, 0);
}

export interface Settlement {
  /** Vente à crédit : part de la valeur qui baisse la créance. */
  reduction: number;
  /** Remboursement maximal (≤ payé − remboursements précédents). */
  refundMax: number;
}

export function settlement(sale: SaleResult, listing: SaleReturns, value: number): Settlement {
  const previous = listing.returns;
  let reduction = 0;
  if (sale.kind === "credit") {
    const outstanding = sale.remaining - previous.reduce((s, r) => s + r.credit_reduction, 0);
    reduction = Math.max(0, Math.min(value, outstanding));
  }
  const refundable = sale.paid - previous.reduce((s, r) => s + (r.refund?.amount ?? 0), 0);
  return { reduction, refundMax: Math.max(0, Math.min(value - reduction, refundable)) };
}

export interface ExchangeBalance {
  /** Avoir versé à la nouvelle vente. */
  applied: number;
  /** Différence que le client paie. */
  toPay: number;
  /** Différence rendue au client (avoir plus grand que la nouvelle vente). */
  toGive: number;
}

export function exchangeBalance(avoir: number, newTotal: number): ExchangeBalance {
  const applied = Math.min(avoir, newTotal);
  return { applied, toPay: newTotal - applied, toGive: avoir - applied };
}
