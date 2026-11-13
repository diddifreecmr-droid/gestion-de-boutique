import { describe, expect, it } from "vitest";
import type { CatalogArticle } from "../../core/gateways/catalogContract";
import { TEXTILE_SHORTCUTS } from "../../testing/textileSale";
import { soldQuantityText } from "./soldQuantity";
import {
  lengthInput,
  maxPieces,
  meterTotal,
  metersText,
  parseLength,
  piecesTenths,
  resolveShortcut,
  stockText,
  tenthsValue,
  toTenths,
  ONE_DECIMAL,
  LENGTH_EMPTY,
} from "./textile";

const plain = (text: string) => text.replace(/\s/g, " ");
const WX: CatalogArticle = {
  id: "wx",
  name: "Wax Fleur de mariage",
  sale_mode: "meter",
  unit_label: "unité",
  base_price: 2500,
  min_price: null,
  available: "54.900",
  piece_length_m: "5.49",
  piece: { length_m: "5.49", base_price: 13000, min_price: null },
};
const shortcut = (code: string) => {
  const found = TEXTILE_SHORTCUTS.find((one) => one.code === code);
  if (found === undefined) throw new Error(code);
  return found;
};

describe("calculs Textile au dixième (QC-3, SCN-L3-02)", () => {
  it("stock servi au dixième ; plus fin : rupture de contrat", () => {
    expect(toTenths("54.900")).toBe(549);
    expect(toTenths("2.9")).toBe(29);
    expect(tenthsValue(25)).toBe("2.5");
    expect(plain(metersText(469))).toBe("46,9 m");
    expect(plain(metersText(30))).toBe("3 m");
    expect(() => toTenths("2.95")).toThrow("hors dixième");
  });

  it("saisie : virgule ou point, une décimale au plus, jamais zéro ni vide", () => {
    expect(parseLength("2,5")).toEqual({ ok: true, tenths: 25 });
    expect(parseLength(" 2.5 ")).toEqual({ ok: true, tenths: 25 });
    expect(parseLength("2,50")).toEqual({ ok: true, tenths: 25 });
    expect(parseLength("2,55")).toEqual({ ok: false, error: ONE_DECIMAL });
    expect(parseLength("")).toEqual({ ok: false, error: LENGTH_EMPTY });
    expect(parseLength("0")).toMatchObject({ ok: false });
    expect(parseLength("2 m")).toMatchObject({ ok: false });
    expect(lengthInput(25)).toBe("2,5");
    expect(lengthInput(30)).toBe("3");
  });

  it("totaux et stock retiré : 2,5 m × 2 500 = 6 250 ; 1 pièce = 5,5 m ; 8 pièces dans 46,9 m", () => {
    expect(meterTotal(25, 2500)).toBe(6250);
    expect(meterTotal(25, 2499)).toBe(6248); // 6 247,5 → demi vers le haut
    expect(piecesTenths(1, "5.49")).toBe(55);
    expect(piecesTenths(2, "5.49")).toBe(110);
    expect(maxPieces(469, "5.49")).toBe(8);
    expect(maxPieces(29, "5.49")).toBe(0);
    expect(plain(stockText(469, "5.49"))).toBe("46,9 m (≈ 8 pièces)");
    expect(plain(stockText(120, undefined))).toBe("12 m");
  });

  it("raccourcis RG-X05 : pièce à la pièce, ou longueur ; demi-pièce 2,7 m ; 6 yards sans longueur", () => {
    expect(resolveShortcut(shortcut("piece"), WX)).toEqual({ mode: "piece", pieces: 1 });
    expect(resolveShortcut(shortcut("half_piece"), WX)).toEqual({ mode: "meter", tenths: 27 });
    expect(resolveShortcut(shortcut("2m"), WX)).toEqual({ mode: "meter", tenths: 20 });
    const byMeter: CatalogArticle = { ...WX };
    delete byMeter.piece;
    expect(resolveShortcut(shortcut("piece"), byMeter)).toEqual({ mode: "meter", tenths: 55 });
    const noLength = { ...byMeter };
    delete noLength.piece_length_m;
    expect(resolveShortcut(shortcut("piece"), noLength)).toEqual({ mode: "meter", tenths: 55 });
    expect(resolveShortcut(shortcut("half_piece"), noLength)).toEqual({
      mode: "meter",
      tenths: 27,
    });
    expect(() => resolveShortcut({ ...shortcut("1m"), basis: "yard" }, WX)).toThrow("inconnu");
  });

  it("quantité affichée d'une ligne vendue : « 2 », « 2,5 m », « 3 pièces »", () => {
    expect(soldQuantityText({ sale_mode: "unit", quantity: "2" })).toBe("2");
    expect(plain(soldQuantityText({ sale_mode: "meter", quantity: "2.500" }))).toBe("2,5 m");
    expect(soldQuantityText({ sale_mode: "piece", quantity: "3" })).toBe("3 pièces");
    expect(() => soldQuantityText({ sale_mode: "yard", quantity: "1" })).toThrow("inconnu");
  });
});
