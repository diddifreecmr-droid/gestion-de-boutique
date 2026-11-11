import { describe, expect, it } from "vitest";
import { FormatError, formatQuantity } from "./index";

const T = " ";
const N = " ";
const M = "−";

describe("formatQuantity", () => {
  it.each<[number | string, string]>([
    [0, "0"],
    [1, "1"],
    [2.5, "2,5"],
    [2.375, "2,375"],
    [0.1 + 0.2, "0,3"],
    [1250, `1${T}250`],
    [1250.75, `1${T}250,75`],
    [-2.5, `${M}2,5`],
    [-0.0001, "0"],
    ["2.500", "2,5"],
    ["4", "4"],
    ["-3.25", `${M}3,25`],
    ["0.000", "0"],
  ])("formate %s", (value, expected) => {
    expect(formatQuantity(value)).toBe(expected);
  });

  it("colle l'unité par une espace insécable", () => {
    expect(formatQuantity(2.5, "m")).toBe(`2,5${N}m`);
  });

  it.each<number | string>([
    Number.NaN,
    Number.POSITIVE_INFINITY,
    1e21,
    "2,5",
    "abc",
    "",
    "1.2345",
  ])("lève une FormatError pour %s", (value) => {
    expect(() => formatQuantity(value)).toThrow(FormatError);
  });
});
