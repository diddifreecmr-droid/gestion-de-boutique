import { describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../../core/api/errors";
import type { CatalogArticle } from "../../core/gateways/catalogContract";
import { priceBelowMinimum, stockInsufficient } from "../../core/gateways/saleErrors";
import { businessDay } from "./buildCommand";
import { newLine, unitStock, withQuantity } from "./draft";
import { readLastPaymentMode, writeLastPaymentMode } from "./lastPaymentMode";
import { normalizePhone } from "./phone";
import { OFFLINE_MESSAGE, saleErrorMessage } from "./saleErrorMessage";

const ARTICLE: CatalogArticle = {
  id: "a1",
  name: "Haojue HJ125-8",
  sale_mode: "unit",
  unit_label: "moto",
  base_price: 780_000,
  min_price: null,
  available: "4",
};

function brokenStorage(): Storage {
  const fail = () => {
    throw new DOMException("refusé", "SecurityError");
  };
  return { getItem: fail, setItem: fail } as unknown as Storage;
}

describe("dernier mode de paiement", () => {
  it("lit et écrit par boutique", () => {
    writeLastPaymentMode("s1", "pm-orange");
    expect(readLastPaymentMode("s1")).toBe("pm-orange");
    expect(readLastPaymentMode("s2")).toBeNull();
  });

  it("stockage indisponible : signalé en console, la vente continue", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    expect(readLastPaymentMode("s1", brokenStorage())).toBeNull();
    expect(() => {
      writeLastPaymentMode("s1", "pm-cash", brokenStorage());
    }).not.toThrow();
    expect(warn).toHaveBeenCalledTimes(2);
  });

  it("refuse une boutique vide", () => {
    expect(() => readLastPaymentMode("")).toThrow("identifiant de boutique vide");
  });
});

describe("téléphone (H20)", () => {
  it.each([
    ["690000000", "+237690000000"],
    ["6 90 00 00 00", "+237690000000"],
    ["+237 677 11 22 33", "+237677112233"],
    ["222 33 44 55", "+237222334455"],
  ])("« %s » → %s", (raw, expected) => {
    expect(normalizePhone(raw)).toBe(expected);
  });

  it.each(["", "69000000", "590000000", "2376900000001"])("« %s » refusé", (raw) => {
    expect(normalizePhone(raw)).toBeNull();
  });
});

describe("brouillon", () => {
  it("une fiche de détail par unité, les saisies gardées", () => {
    const line = newLine(ARTICLE);
    const first = { ...line, units: [{ color: "Rouge", chassis: "", engine: "" }] };
    const grown = withQuantity(first, 3);
    expect(grown.units).toHaveLength(3);
    expect(grown.units[0]?.color).toBe("Rouge");
    expect(withQuantity(grown, 1).units).toEqual(first.units);
  });

  it("stock non entier ou rupture : erreur explicite", () => {
    expect(() => unitStock({ ...ARTICLE, available: "2.5" })).toThrow("Stock non entier");
    expect(() => newLine({ ...ARTICLE, available: "0" })).toThrow("en rupture");
  });

  it("jour métier à Douala", () => {
    expect(businessDay(new Date("2026-11-10T23:30:00Z"))).toBe("2026-11-11");
    expect(businessDay(new Date("2026-11-10T22:59:00Z"))).toBe("2026-11-10");
  });
});

describe("erreurs de vente", () => {
  const line = newLine(ARTICLE);

  it("coupure réseau → « Connexion nécessaire »", () => {
    expect(saleErrorMessage(new NetworkError("x"), [line], "Garoua")).toBe(OFFLINE_MESSAGE);
  });

  it("stock insuffisant sans autre lieu", () => {
    const error = new ApiError(422, "STOCK_INSUFFICIENT", "x", {
      article_id: "a1",
      available: "0",
      other_locations: [],
    });
    expect(saleErrorMessage(error, [line], "Garoua")).toBe(
      "Stock insuffisant pour Haojue HJ125-8 : 0 disponible à Garoua. Aucun stock dans les autres lieux.",
    );
  });

  it("code inconnu : message du serveur et code", () => {
    const error = new ApiError(409, "VERSION_CONFLICT", "Objet modifié");
    expect(saleErrorMessage(error, [], "Garoua")).toBe(
      "La vente n'a pas été enregistrée : Objet modifié (VERSION_CONFLICT).",
    );
    expect(saleErrorMessage(new ApiError(403, "FORBIDDEN", "x"), [], "Garoua")).toMatch(
      /pas le droit/,
    );
    expect(saleErrorMessage(new ApiError(422, "OVERPAYMENT", "x"), [], "Garoua")).toMatch(
      /dépasse/,
    );
  });

  it("une erreur hors contrat est relancée (fail-fast)", () => {
    expect(() => saleErrorMessage(new TypeError("bug"), [], "Garoua")).toThrow("bug");
  });

  it("détails mal formés : rupture de contrat explicite", () => {
    expect(() =>
      stockInsufficient(new ApiError(422, "STOCK_INSUFFICIENT", "x", { available: "1" })),
    ).toThrow("other_locations");
    expect(() =>
      stockInsufficient(
        new ApiError(422, "STOCK_INSUFFICIENT", "x", {
          article_id: "a1",
          available: "1",
          other_locations: [42],
        }),
      ),
    ).toThrow("other_locations");
    expect(() =>
      priceBelowMinimum(
        new ApiError(422, "PRICE_BELOW_MINIMUM", "x", {
          article_id: "a1",
          line: 1,
          min_price: 1.5,
        }),
      ),
    ).toThrow("request_required");
    expect(() =>
      priceBelowMinimum(
        new ApiError(422, "PRICE_BELOW_MINIMUM", "x", {
          article_id: "a1",
          line: 1,
          min_price: 1.5,
          request_required: true,
        }),
      ),
    ).toThrow("min_price");
  });
});
