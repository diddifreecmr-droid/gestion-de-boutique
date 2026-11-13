/**
 * Retours et échanges du faux serveur des ventes (tests seulement), mêmes règles que T16b :
 * quantité ≤ encore rendable (`RETURN_QUANTITY_EXCEEDED`), châssis à préciser sur une ligne
 * rendue en partie, valeur = quantité × prix (reste exact au dernier retour), baisse de la
 * créance d'abord, remboursement ≤ payé net (`OVERPAYMENT`), échange : avoir versé à la
 * nouvelle vente dans `exchange.mode_id`. Coûts et marges : propriétaire seulement.
 */
import type {
  ReturnedLine,
  SaleReturn,
  SaleReturnCommand,
  SaleReturns,
} from "../core/gateways/returnsContract";
import type { SaleResult } from "../core/gateways/salesContract";
import { businessDay } from "../features/sales/buildCommand";
import { apiError, json, type Call } from "./fakeApi";
import { NOW, TODAY } from "./salesFixtures";
import { addSale, type SaleServer } from "./salesServer";

const key = (text: string) => text.toUpperCase().replace(/[^A-Z0-9]/g, "");

function previous(server: SaleServer, saleId: string): SaleReturn[] {
  return server.returns.get(saleId) ?? [];
}

function doneOn(returns: readonly SaleReturn[], line: number) {
  const lines = returns.flatMap((made) => made.lines).filter((done) => done.line === line);
  return {
    quantity: lines.reduce((sum, done) => sum + Number(done.quantity), 0),
    amount: lines.reduce((sum, done) => sum + done.amount, 0),
    chassis: new Set(lines.flatMap((done) => done.chassis.map(key))),
  };
}

export function listing(server: SaleServer, sale: SaleResult): SaleReturns {
  const returns = previous(server, sale.id);
  return {
    sale_id: sale.id,
    returns,
    balances: sale.lines.map((line, index) => {
      const done = doneOn(returns, index + 1).quantity;
      const sold = Number(line.quantity);
      return {
        line: index + 1,
        article_id: line.article_id,
        sold: String(sold),
        returned: String(done),
        returnable: String(sold - done),
      };
    }),
  };
}

function returnedLines(server: SaleServer, sale: SaleResult, body: SaleReturnCommand) {
  const returns = previous(server, sale.id);
  return body.lines.map((wanted): ReturnedLine | Response => {
    const sold = sale.lines[wanted.line - 1];
    if (sold === undefined) throw new Error(`Faux serveur : ligne ${String(wanted.line)} inconnue`);
    const done = doneOn(returns, wanted.line);
    const quantity = Number(wanted.quantity);
    const left = Number(sold.quantity) - done.quantity;
    if (quantity > left) {
      return apiError(422, "RETURN_QUANTITY_EXCEEDED", "Quantité rendue trop grande", {
        line: wanted.line,
        returnable: String(left),
      });
    }
    const full = quantity === left;
    const available = sold.details
      .map((detail) => detail.chassis_number)
      .filter((c): c is string => c !== null && !done.chassis.has(key(c)));
    const asked = wanted.chassis ?? [];
    if (!full && available.length > 0 && asked.length === 0) {
      return apiError(400, "VALIDATION_ERROR", "Précisez les châssis", { field: "lines.chassis" });
    }
    const amount = full ? sold.line_total - done.amount : Math.round(quantity * sold.unit_price);
    const cost = "frozen_last_cost" in sold ? (sold.frozen_last_cost ?? null) : undefined;
    const base: ReturnedLine = {
      line: wanted.line,
      article_id: sold.article_id,
      article_name: sold.article_name,
      quantity: String(quantity),
      stock_quantity: String(quantity),
      stock_unit: "unit",
      condition: wanted.condition,
      amount,
      chassis: (asked.length > 0 ? asked : full ? available : []).map(key),
    };
    if (cost === undefined) return base;
    const margin = cost === null ? null : amount - cost * quantity;
    return { ...base, cost: cost === null ? null : cost * quantity, margin, margin_wac: margin };
  });
}

function settle(server: SaleServer, sale: SaleResult, value: number) {
  const returns = previous(server, sale.id);
  const reduced = returns.reduce((sum, made) => sum + made.credit_reduction, 0);
  const reduction =
    sale.kind === "credit" ? Math.max(0, Math.min(value, sale.remaining - reduced)) : 0;
  const refunded = returns.reduce((sum, made) => sum + (made.refund?.amount ?? 0), 0);
  return { reduction, max: Math.max(0, Math.min(value - reduction, sale.paid - refunded)) };
}

/**
 * Droits de l'échange (T29, QC-4) : retour simple = propriétaire ; échange de l'employé si le
 * réglage est actif (403 `details.setting` sinon), dans le délai (422 `EXCHANGE_PERIOD_OVER`).
 */
function exchangeRefusal(server: SaleServer, sale: SaleResult, body: SaleReturnCommand) {
  if (server.role === "owner") return null;
  if (body.exchange === null || body.exchange === undefined) {
    return apiError(403, "FORBIDDEN", "Réservé au propriétaire", { permission: "sale.return" });
  }
  if (!server.exchange.employeeAllowed) {
    return apiError(403, "FORBIDDEN", "Échange de l'employé non autorisé", {
      permission: "sale.exchange",
      setting: "employee_exchange_allowed",
    });
  }
  const days = server.exchange.days;
  if (days === null) return null;
  const deadline = new Date(`${sale.sold_on}T00:00:00Z`);
  deadline.setUTCDate(deadline.getUTCDate() + days);
  const last = deadline.toISOString().slice(0, 10);
  if (businessDay() <= last) return null;
  return apiError(422, "EXCHANGE_PERIOD_OVER", "Délai d'échange dépassé", {
    sold_on: sale.sold_on,
    exchange_days: days,
    deadline: last,
  });
}

export async function recordReturn(
  server: SaleServer,
  sale: SaleResult,
  call: Call,
): Promise<Response> {
  const body = call.body as SaleReturnCommand;
  server.recordReturn(sale.id, body);
  const denied = exchangeRefusal(server, sale, body);
  if (denied !== null) return denied;
  if (sale.status !== "valid") {
    return apiError(409, "INVALID_STATE_TRANSITION", "Vente annulée", { status: sale.status });
  }
  const lines = returnedLines(server, sale, body);
  const refused = lines.find((line) => line instanceof Response);
  if (refused !== undefined) return refused;
  const kept = lines.filter((line): line is ReturnedLine => !(line instanceof Response));
  const amount = kept.reduce((sum, line) => sum + line.amount, 0);
  const { reduction, max } = settle(server, sale, amount);
  let refund = body.refund ?? null;
  let exchangeSale: SaleResult | null = null;
  if (body.exchange !== null && body.exchange !== undefined) {
    const { sale: wanted, mode_id } = body.exchange;
    refund = max > 0 ? { amount: max, mode_id, refunded_on: TODAY } : null;
    const total = wanted.lines.reduce((s, l) => s + Number(l.quantity) * l.unit_price, 0);
    const applied = Math.min(max, total);
    const avoir = { mode_id, amount: applied, reference: `Échange ${sale.number}` };
    const payments = [...(wanted.payments ?? []), ...(applied > 0 ? [avoir] : [])];
    exchangeSale = await addSale(server, { ...wanted, location_id: sale.location_id, payments });
  } else if (refund !== null && refund.amount > max) {
    return apiError(422, "OVERPAYMENT", "Remboursement trop grand", {
      field: "refund.amount",
      refund: refund.amount,
      max,
    });
  }
  const margins = kept.map((line) => line.margin);
  const margin = margins.some((m) => m === null || m === undefined)
    ? null
    : margins.reduce<number>((s, m) => s + (m ?? 0), 0);
  const made: SaleReturn = {
    id: body.id ?? `ret-${String(previous(server, sale.id).length + 1)}`,
    sale_id: sale.id,
    sale_number: sale.number,
    kind: exchangeSale === null ? "return" : "exchange",
    lines: kept,
    reason: body.reason,
    amount,
    refund: refund === null ? null : { ...refund, refunded_on: refund.refunded_on ?? TODAY },
    credit_reduction: reduction,
    exchange_sale_id: exchangeSale?.id ?? null,
    returned_at: NOW,
    returned_on: TODAY,
    created_by: server.userId,
    // La marge seulement pour le propriétaire (TR-05) ; l'employé qui échange ne la voit pas.
    ...(server.role === "owner" ? { margin, margin_wac: margin } : {}),
  };
  server.returns.set(sale.id, [...previous(server, sale.id), made]);
  return json(201, exchangeSale === null ? made : { ...made, exchange_sale: exchangeSale });
}
