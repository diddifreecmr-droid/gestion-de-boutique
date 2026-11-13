import { describe, expect, it } from "vitest";
import { ApiError } from "../../core/api/errors";
import { importBatch } from "../../testing/imports";
import { blockingTexts, dayMonth, rowsText, stillCancellable } from "./batchText";
import { cancelFailure } from "./cancelErrors";
import { OFFLINE } from "./importErrors";
import { NetworkError } from "../../core/api/errors";

describe("textes des lots d'import", () => {
  it("JJ/MM, délai inclus, lignes importées et ignorées", () => {
    expect(dayMonth("2026-11-20")).toBe("20/11");
    expect(() => dayMonth("20/11/2026")).toThrow("Date de lot invalide");
    const batch = importBatch();
    expect(stillCancellable(batch, "2026-11-20")).toBe(true);
    expect(stillCancellable(batch, "2026-11-21")).toBe(false);
    expect(stillCancellable(importBatch({ status: "cancelled" }), "2026-11-13")).toBe(false);
    expect(rowsText(importBatch({ rows_imported: 1, rows_ignored: 0 }))).toBe("1 ligne importée");
  });

  it("opérations bloquantes : les 8 types en français ; inconnu ou illisible → erreur", () => {
    const types = ["sale", "return", "purchase", "adjustment", "inventory", "payment"];
    const all = [...types, "receivable", "import"].map((type) => ({ type, number: "N-1" }));
    expect(blockingTexts(all)).toEqual([
      "la vente N-1",
      "le retour N-1",
      "l'achat N-1",
      "l'ajustement N-1",
      "l'inventaire N-1",
      "le versement N-1",
      "la créance N-1",
      "le lot N-1",
    ]);
    expect(() => blockingTexts([{ type: "transfer", number: "T-1" }])).toThrow("inconnu");
    expect(() => blockingTexts([{ type: "sale" }])).toThrow("sans type ou numéro");
    expect(() => blockingTexts(undefined)).toThrow("details.blocking absent");
  });

  it("annulation refusée : réseau, code inconnu lisible ; erreur imprévue relancée", () => {
    const batch = importBatch();
    expect(cancelFailure(new NetworkError("hors ligne"), batch).text).toBe(OFFLINE);
    expect(cancelFailure(new ApiError(500, "BOOM", "Panne", {}), batch).text).toContain("BOOM");
    expect(() => cancelFailure(new TypeError("bug"), batch)).toThrow("bug");
  });
});
