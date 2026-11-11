import { describe, expect, it } from "vitest";
import { groupThousands, withSign } from "./number";

describe("groupThousands", () => {
  it("groupe par trois avec U+202F", () => {
    expect(groupThousands("1234567")).toBe("1 234 567");
    expect(groupThousands("123")).toBe("123");
  });

  it("refuse autre chose que des chiffres", () => {
    expect(() => groupThousands("-12")).toThrow("groupThousands attend des chiffres");
    expect(() => groupThousands("")).toThrow();
  });
});

describe("withSign", () => {
  it("préfixe U+2212 seulement si négatif", () => {
    expect(withSign("5", true)).toBe("−5");
    expect(withSign("5", false)).toBe("5");
  });
});
