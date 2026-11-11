import { describe, expect, it } from "vitest";
import { ApiError, NetworkError } from "../../../core/api/errors";
import type { SaleReturn, SaleReturns } from "../../../core/gateways/returnsContract";
import type { SaleResult } from "../../../core/gateways/salesContract";
import { returnErrorMessage, RETURN_OFFLINE } from "./returnErrorMessage";
import { exchangeBalance, returnValue, settlement } from "./returnMath";

const SALE = {
  kind: "cash",
  total: 1_000,
  paid: 1_000,
  remaining: 0,
  lines: [{ quantity: "3", unit_price: 333, line_total: 1_000 }],
} as unknown as SaleResult;

const PAST = { lines: [{ line: 1, amount: 333 }], credit_reduction: 0, refund: { amount: 333 } };

function listing(returnable: string, returns: unknown[] = []): SaleReturns {
  return {
    sale_id: "s",
    returns: returns as SaleReturn[],
    balances: [{ line: 1, article_id: "a", sold: "3", returned: "0", returnable }],
  };
}

describe("valeur rendue et règlement (mêmes règles que le serveur)", () => {
  it("partiel : quantité × prix ; dernier retour : le reste exact de la ligne", () => {
    expect(returnValue(SALE, listing("3"), { 1: { quantity: 1 } })).toBe(333);
    expect(returnValue(SALE, listing("2", [PAST]), { 1: { quantity: 2 } })).toBe(667);
    expect(returnValue(SALE, listing("3"), { 1: { quantity: 0 } })).toBe(0);
    expect(() => returnValue(SALE, listing("3"), { 2: { quantity: 1 } })).toThrow("inconnue");
  });

  it("comptant : remboursement ≤ payé moins les remboursements précédents", () => {
    expect(settlement(SALE, listing("2", [PAST]), 667)).toEqual({ reduction: 0, refundMax: 667 });
    const paidLess = { ...SALE, paid: 500 };
    expect(settlement(paidLess, listing("2", [PAST]), 667).refundMax).toBe(167);
  });

  it("crédit : la créance baisse d'abord, le reste est remboursable", () => {
    const credit = { ...SALE, kind: "credit", paid: 200, remaining: 800 };
    expect(settlement(credit, listing("3"), 1_000)).toEqual({ reduction: 800, refundMax: 200 });
    expect(settlement(credit, listing("3"), 500)).toEqual({ reduction: 500, refundMax: 0 });
  });

  it("échange : différence payée ou rendue", () => {
    expect(exchangeBalance(650, 780)).toEqual({ applied: 650, toPay: 130, toGive: 0 });
    expect(exchangeBalance(650, 620)).toEqual({ applied: 620, toPay: 0, toGive: 30 });
  });
});

describe("messages de refus d'un retour", () => {
  const say = (error: unknown) => returnErrorMessage(error, [], "Garoua");
  it("chaque code prévu est dit en clair", () => {
    expect(say(new NetworkError("x"))).toBe(RETURN_OFFLINE);
    expect(
      say(new ApiError(422, "OVERPAYMENT", "x", { field: "refund.amount", refund: 9, max: 5 })),
    ).toMatch(/au plus 5\sFCFA/);
    expect(say(new ApiError(422, "OVERPAYMENT", "x", { total: 1, paid: 2 }))).toMatch(
      /nouvelle vente/,
    );
    expect(say(new ApiError(409, "INVALID_STATE_TRANSITION", "x"))).toMatch(/annulée/);
    expect(say(new ApiError(400, "VALIDATION_ERROR", "x", { field: "lines.chassis" }))).toMatch(
      /Châssis/,
    );
    expect(say(new ApiError(400, "VALIDATION_ERROR", "Date"))).toBe("Retour refusé : Date.");
    expect(say(new ApiError(403, "FORBIDDEN", "x"))).toMatch(/propriétaire/);
    expect(
      say(new ApiError(422, "PAYMENT_INCOMPLETE", "x", { total: 2, paid: 1, remaining: 1 })),
    ).toMatch(/il manque/);
  });

  it("une erreur hors contrat est relancée (fail-fast)", () => {
    expect(() => say(new Error("bug"))).toThrow("bug");
    expect(() => say(new ApiError(422, "RETURN_QUANTITY_EXCEEDED", "x", {}))).toThrow("line");
  });
});
