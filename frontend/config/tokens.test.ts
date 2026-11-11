// @vitest-environment node
import { describe, expect, it } from "vitest";
import { readToken, readTokenFromFile } from "./tokens";

describe("readToken", () => {
  it("lit la couleur primaire dans tokens.css", () => {
    expect(readTokenFromFile("--color-primary")).toBe("#0B5D7A");
    expect(readTokenFromFile("--color-bg")).toBe("#F6F7F9");
  });

  it("échoue si le token est absent", () => {
    expect(() => readToken("--a: 1;", "--color-primary")).toThrow("0 définition(s)");
  });

  it("échoue si le token est défini deux fois", () => {
    expect(() => readToken("--x: 1;\n--x: 2;", "--x")).toThrow("2 définition(s)");
  });

  it("refuse un nom invalide", () => {
    expect(() => readToken("", "color")).toThrow("Nom de token invalide");
  });
});
