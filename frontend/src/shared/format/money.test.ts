import { describe, expect, it } from "vitest";
import { FormatError, formatMoney } from "./index";

// Rendre visibles les espaces spéciales dans les attentes.
const T = " "; // espace fine insécable (milliers)
const N = " "; // espace insécable (avant FCFA)
const M = "−"; // signe moins

describe("formatMoney", () => {
  it.each([
    [0, `0${N}FCFA`],
    [5, `5${N}FCFA`],
    [999, `999${N}FCFA`],
    [1000, `1${T}000${N}FCFA`],
    [780000, `780${T}000${N}FCFA`],
    [1250000, `1${T}250${T}000${N}FCFA`],
    [12500000, `12${T}500${T}000${N}FCFA`],
    [Number.MAX_SAFE_INTEGER, `9${T}007${T}199${T}254${T}740${T}991${N}FCFA`],
  ])("formate %d", (amount, expected) => {
    expect(formatMoney(amount)).toBe(expected);
  });

  it("utilise U+202F entre milliers et U+00A0 avant FCFA", () => {
    expect(formatMoney(1250000)).toBe("1 250 000 FCFA");
  });

  it.each([
    [-1, `${M}1${N}FCFA`],
    [-610000, `${M}610${T}000${N}FCFA`],
  ])("signe une marge négative %d avec « − »", (amount, expected) => {
    expect(formatMoney(amount)).toBe(expected);
  });

  it("n'affiche jamais « −0 »", () => {
    expect(formatMoney(-0)).toBe(`0${N}FCFA`);
  });

  it.each([1.5, 0.1, Number.NaN, Number.POSITIVE_INFINITY, Number.MAX_SAFE_INTEGER + 1])(
    "lève une FormatError pour %d",
    (amount) => {
      expect(() => formatMoney(amount)).toThrow(FormatError);
    },
  );

  it("donne un message explicite", () => {
    expect(() => formatMoney(12.5)).toThrow("Montant invalide : 12.5 (entier FCFA attendu)");
  });
});
