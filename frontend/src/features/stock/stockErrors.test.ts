import { describe, expect, it } from "vitest";
import { ApiError, NetworkError } from "../../core/api/errors";
import {
  failureText,
  FORBIDDEN_MESSAGE,
  INVENTORY_CONFLICT,
  loadFailureMessage,
  OFFLINE_SAVE,
  stockFailure,
} from "./stockErrors";
import { stockRole } from "./stockRoles";

const api = (code: string, details: Record<string, unknown> = {}, message = "Refus") =>
  new ApiError(422, code, message, details);

describe("stockFailure — refus traduits, rien d'avalé", () => {
  it("réseau, droit, conflit, inventaire déjà ouvert, motifs, message du serveur", () => {
    expect(stockFailure(new NetworkError("x"))).toEqual({ kind: "message", text: OFFLINE_SAVE });
    expect(stockFailure(api("FORBIDDEN"))).toEqual({ kind: "message", text: FORBIDDEN_MESSAGE });
    expect(stockFailure(api("VERSION_CONFLICT"))).toEqual({ kind: "conflict" });
    expect(stockFailure(api("INVENTORY_IN_PROGRESS", { inventory_id: null }))).toEqual({
      kind: "inventoryOpen",
      inventoryId: null,
    });
    expect(stockFailure(api("VALIDATION_ERROR", { field: "reasons", articles: ["a"] }))).toEqual({
      kind: "reasons",
      articleIds: ["a"],
    });
    expect(stockFailure(api("VALIDATION_ERROR", { field: "note" }, "Note vide"))).toEqual({
      kind: "message",
      text: "Note vide",
    });
    expect(stockFailure(api("OTHER", {}, "Autre refus"))).toEqual({
      kind: "message",
      text: "Autre refus",
    });
  });

  it("stock insuffisant sans autre lieu", () => {
    const error = api("STOCK_INSUFFICIENT", { available: "0", other_locations: [] });
    expect(stockFailure(error, "Garoua")).toEqual({
      kind: "message",
      text: "Stock insuffisant : 0 disponible à Garoua.",
    });
  });

  it("fail-fast : erreur imprévue relancée, détails mal formés refusés", () => {
    const bug = new TypeError("bug");
    expect(() => stockFailure(bug)).toThrow(bug);
    expect(() => stockFailure(api("STOCK_INSUFFICIENT", {}))).toThrow(/available/);
    expect(() =>
      stockFailure(api("STOCK_INSUFFICIENT", { available: "1", other_locations: [{}] })),
    ).toThrow(/other_locations/);
    expect(() => stockFailure(api("INVENTORY_IN_PROGRESS", { inventory_id: 3 }))).toThrow();
    expect(() =>
      stockFailure(api("VALIDATION_ERROR", { field: "reasons", articles: [1] })),
    ).toThrow(/articles/);
    expect(() => stockRole("driver")).toThrow(/chauffeur|driver/);
  });

  it("textes des refus et des lectures", () => {
    expect(failureText({ kind: "conflict" })).toBe(INVENTORY_CONFLICT);
    expect(failureText({ kind: "inventoryOpen", inventoryId: null })).toMatch(/déjà en cours/);
    expect(failureText({ kind: "reasons", articleIds: [] })).toMatch(/motif/);
    expect(loadFailureMessage(api("NOT_FOUND"))).toMatch(/introuvable/);
    expect(loadFailureMessage(api("FORBIDDEN"))).toBe(FORBIDDEN_MESSAGE);
    expect(loadFailureMessage(api("X", {}, "Refus X"))).toBe("Refus X");
  });
});
