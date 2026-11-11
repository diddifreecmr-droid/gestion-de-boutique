import { describe, expect, it } from "vitest";
import { ApiError } from "../../../core/api/errors";
import { PRICE_REQUEST_PROBLEMS, priceBelowMinimum } from "../../../core/gateways/saleErrors";
import type { PriceRequest } from "../../../core/gateways/salesContract";
import { approvalView } from "./approvalView";
import { problemMessage, remainingText, statusAt } from "./priceRequestText";

const NOW = Date.parse("2026-11-11T10:00:00Z");
const REQUEST: PriceRequest = {
  id: "pr-1",
  seller_id: "u1",
  article_id: "a1",
  article_name: "Haojue HJ125-8",
  location_id: "l1",
  requested_price: 700_000,
  min_price: 720_000,
  status: "pending",
  requested_at: "2026-11-11T10:00:00Z",
  expires_at: "2026-11-11T10:30:00Z",
  decided_by: null,
  decided_at: null,
  sale_id: null,
  version: 1,
};

const refused = (problem: unknown) =>
  new ApiError(422, "PRICE_BELOW_MINIMUM", "x", {
    article_id: "a1",
    line: 1,
    min_price: 720_000,
    request_required: true,
    ...(problem === undefined ? {} : { price_request: problem }),
  });

describe("raisons de PRICE_BELOW_MINIMUM.details.price_request (T16b)", () => {
  it.each(PRICE_REQUEST_PROBLEMS)("« %s » : lue et dite en clair", (problem) => {
    expect(priceBelowMinimum(refused(problem)).price_request).toBe(problem);
    const text = problemMessage(problem, REQUEST);
    expect(text.length).toBeGreaterThan(20);
    expect(text).not.toMatch(/undefined|null/);
  });

  it("chaque raison a son propre message", () => {
    const texts = PRICE_REQUEST_PROBLEMS.map((problem) => problemMessage(problem, REQUEST));
    expect(new Set(texts).size).toBe(PRICE_REQUEST_PROBLEMS.length);
    expect(problemMessage("price_too_low", REQUEST)).toMatch(/au moins 700\s000\sFCFA/);
    expect(problemMessage("price_too_low", null)).toMatch(/remontez-le/);
  });

  it("raison absente → null ; raison inconnue → rupture de contrat (fail-fast)", () => {
    expect(priceBelowMinimum(refused(undefined)).price_request).toBeNull();
    expect(() => priceBelowMinimum(refused("bizarre"))).toThrow("price_request");
  });
});

describe("statut et temps restant", () => {
  it("expirée à l'heure pile, acceptée et utilisée reste acceptée", () => {
    expect(statusAt(REQUEST, NOW)).toBe("pending");
    expect(statusAt(REQUEST, Date.parse(REQUEST.expires_at))).toBe("expired");
    const used = { ...REQUEST, status: "accepted", sale_id: "s1" };
    expect(statusAt(used, Date.parse(REQUEST.expires_at) + 1)).toBe("accepted");
    expect(() => statusAt({ ...REQUEST, status: "bizarre" }, NOW)).toThrow("inconnu");
  });

  it("« 30 min », puis « moins d'une minute »", () => {
    expect(remainingText(REQUEST, NOW)).toBe("30 min");
    expect(remainingText(REQUEST, Date.parse("2026-11-11T10:29:30Z"))).toBe("moins d'une minute");
  });

  it("vue de la barre : aucune, plusieurs, envoi, refus", () => {
    expect(approvalView(0, false, null, NOW)).toEqual({ kind: "none" });
    expect(approvalView(2, false, REQUEST, NOW)).toEqual({ kind: "several" });
    expect(approvalView(1, true, null, NOW)).toEqual({ kind: "sending" });
    expect(approvalView(1, false, { ...REQUEST, status: "refused" }, NOW)).toEqual({
      kind: "refused",
    });
  });
});
