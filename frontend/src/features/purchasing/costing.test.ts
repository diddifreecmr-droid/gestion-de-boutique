import { describe, expect, it } from "vitest";
import { allocateFees, costPurchase, lineTotal, stockTenths, type CostInput } from "./costing";
import { parseEntryQuantity, quantityInput, quantityWithUnit, unitsFor } from "./units";

const unit = (quantity: string, unitPrice: number): CostInput => ({
  quantity,
  unit: "UNIT",
  unitPrice,
  stockUnit: "UNIT",
  pieceLengthM: null,
});

describe("chiffrage indicatif (même règle que domain/purchasing/costing.py)", () => {
  it("CDC § 17.5 : 20 x 520 000 + douane 400 000 → 540 000 FCFA", () => {
    const costing = costPurchase([unit("20", 520000)], [400000]);
    expect(costing).toEqual({
      lines: [{ total: 10400000, feeShare: 400000, finalUnitCost: 540000 }],
      merchandise: 10400000,
      fees: 400000,
      total: 10800000,
    });
  });

  it("SCN-03 c : 3 x 133 333 pour 400 000 (somme exacte des frais, arrondi au franc)", () => {
    const costing = costPurchase([unit("3", 100000)], [100000]);
    expect(costing.lines[0]?.finalUnitCost).toBe(133333);
    expect(costing.total).toBe(400000);
  });

  it("frais : reste à la plus forte ligne, la première en cas d'égalité", () => {
    expect(allocateFees([1000000, 300000], 100001)).toEqual([76924, 23077]);
    expect(allocateFees([100, 100, 100], 100)).toEqual([34, 33, 33]);
    expect(allocateFees([0, 0], 0)).toEqual([0, 0]);
    expect(allocateFees([0, 0], 10)).toBeNull();
    expect(costPurchase([unit("1", 0)], [10]).lines[0]?.finalUnitCost).toBeNull();
  });

  it("demi-franc vers le haut : 0,5 m à 3 001 FCFA = 1 500,5 → 1 501", () => {
    expect(lineTotal("0.5", 3001)).toBe(1501);
    expect(lineTotal("2.5", 1000)).toBe(2500);
    expect(() => lineTotal("1", -1)).toThrow();
    expect(() => lineTotal("abc", 1)).toThrow();
  });

  it("RG-X02 : 10 yd → 9,1 m ; 0,5 yd → 0,5 m ; 2 pièces de 5,5 m → 11 m", () => {
    const meter = { stockUnit: "METER", pieceLengthM: "5.5" } as const;
    expect(stockTenths({ ...meter, quantity: "10", unit: "YARD" })).toBe(91n);
    expect(stockTenths({ ...meter, quantity: "0.5", unit: "YARD" })).toBe(5n);
    expect(stockTenths({ ...meter, quantity: "2", unit: "PIECE" })).toBe(110n);
    expect(stockTenths({ ...meter, quantity: "2.5", unit: "METER" })).toBe(25n);
    expect(() =>
      stockTenths({ quantity: "1", unit: "YARD", stockUnit: "UNIT", pieceLengthM: null }),
    ).toThrow();
    expect(() =>
      stockTenths({ quantity: "1", unit: "PIECE", stockUnit: "METER", pieceLengthM: null }),
    ).toThrow();
  });
});

describe("unités saisies", () => {
  it("propose les unités compatibles avec l'unité de stock", () => {
    expect(unitsFor({ stock_unit: "UNIT", sold_by_piece: false, piece_length_m: null })).toEqual([
      "UNIT",
    ]);
    expect(unitsFor({ stock_unit: "PIECE", sold_by_piece: false, piece_length_m: null })).toEqual([
      "PIECE",
    ]);
    expect(unitsFor({ stock_unit: "METER", sold_by_piece: false, piece_length_m: null })).toEqual([
      "METER",
      "YARD",
    ]);
    expect(() =>
      unitsFor({ stock_unit: "KG", sold_by_piece: false, piece_length_m: null }),
    ).toThrow();
  });

  it("lit les quantités tapées et les réaffiche", () => {
    expect(parseEntryQuantity(" 2,50 ", "METER")).toEqual({ ok: true, value: "2.5" });
    expect(parseEntryQuantity("3,0", "UNIT")).toEqual({ ok: true, value: "3" });
    expect(parseEntryQuantity("", "UNIT").ok).toBe(false);
    expect(parseEntryQuantity("deux", "UNIT").ok).toBe(false);
    expect(parseEntryQuantity("0", "UNIT").ok).toBe(false);
    expect(quantityInput("9.10")).toBe("9,1");
    expect(quantityInput("20")).toBe("20");
    expect(quantityWithUnit("9.1", "METER")).toBe("9,1 m");
  });
});
