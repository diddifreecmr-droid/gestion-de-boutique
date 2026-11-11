import { describe, expect, it } from "vitest";
import { COLUMNS, stockRow } from "../../testing/stock";
import { isZero, parseQuantity, signedQuantityText, toInput } from "./quantities";
import { basePriceOf, costsOf, stockLine, type SellerStockLine } from "./stockView";

describe("stockLine — vue par rôle (TR-05, RG-D02)", () => {
  it("vendeur : aucun champ de coût, même si le serveur en envoyait (défense en profondeur)", () => {
    const leaked = { ...stockRow("owner"), wac: 1, last_cost: 2, wac_value: 3 };
    const view = stockLine("seller", leaked, COLUMNS);
    expect(view.kind).toBe("seller");
    expect("costs" in view).toBe(false);
    expect(JSON.stringify(view)).not.toMatch(/cost|wac|value/i);
    expect(costsOf(view)).toBeNull();
    expect(basePriceOf(view)).toBe(780000);
    const seller = view as SellerStockLine;
    // @ts-expect-error — le type de la vue vendeur n'a pas de champ de coût (non-fuite typée).
    expect(seller.costs).toBeUndefined();
  });

  it("comptable : coûts sans prix de base ; propriétaire : les deux", () => {
    const accountant = stockLine("accountant", stockRow("accountant"), COLUMNS);
    expect(basePriceOf(accountant)).toBeUndefined();
    expect(costsOf(accountant)).toEqual({ lastCost: 650000, wac: 640000, value: 640000 });
    const owner = stockLine("owner", stockRow("owner"), COLUMNS);
    expect(basePriceOf(owner)).toBe(780000);
    expect(owner.places.map((place) => place.name)).toEqual(["Garoua", "Ngaoundéré"]);
  });

  it("contrat rompu : coût absent pour le comptable, case absente, pastille inconnue", () => {
    expect(() => stockLine("accountant", stockRow("seller"), COLUMNS)).toThrow(/« last_cost »/);
    const missing = { ...stockRow("owner"), cells: [] };
    expect(() => stockLine("owner", missing, COLUMNS)).toThrow(/Case absente/);
    const odd = { ...stockRow("owner"), stock_status: "bizarre" } as never;
    expect(() => stockLine("owner", odd, COLUMNS)).toThrow(/Pastille/);
  });
});

describe("quantités", () => {
  it("lit la saisie : virgule, entier pour une moto, mètres à 3 décimales", () => {
    expect(parseQuantity("2,5", "METER", false)).toEqual({ ok: true, value: "2.5" });
    expect(parseQuantity("1,5", "UNIT", false)).toEqual({
      ok: false,
      error: "Cet article se compte en nombre entier",
    });
    expect(parseQuantity("0", "UNIT", false).ok).toBe(false);
    expect(parseQuantity("0", "UNIT", true)).toEqual({ ok: true, value: "0" });
    expect(parseQuantity("", "UNIT", true).ok).toBe(false);
    expect(parseQuantity("abc", "UNIT", true).ok).toBe(false);
    expect(parseQuantity("1,2345", "METER", true).ok).toBe(false);
    expect(() => parseQuantity("1", "LITRE", true)).toThrow(/Unité de stock inconnue/);
  });

  it("affiche signé et convertit pour un champ", () => {
    expect(signedQuantityText("2.000", "UNIT")).toBe("+2");
    expect(signedQuantityText("-1.500", "METER")).toBe("−1,5 m");
    expect(toInput("2.500")).toBe("2,5");
    expect(toInput("3.000")).toBe("3");
    expect(toInput(null)).toBe("");
    expect(isZero("0.000")).toBe(true);
  });
});
