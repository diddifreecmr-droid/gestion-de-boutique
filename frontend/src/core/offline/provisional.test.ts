import { describe, expect, it } from "vitest";
import { deviceCode, provisionalNumber } from "./provisional";

const DEVICE = "01890a5d-ac96-774b-bcce-b302099a3f2a";

describe("numéro provisoire (RG-T06)", () => {
  it("4 derniers chiffres hexadécimaux de l'appareil, séquence sur 4 chiffres", () => {
    expect(deviceCode(DEVICE)).toBe("3F2A");
    expect(provisionalNumber("V", DEVICE, 7)).toBe("V-HL-3F2A-0007");
    expect(provisionalNumber("D", DEVICE, 12345)).toBe("D-HL-3F2A-12345");
  });

  it("refuse un appareil illisible ou une séquence invalide", () => {
    expect(() => deviceCode("xyz")).toThrow(/illisible/);
    expect(() => provisionalNumber("V", DEVICE, 0)).toThrow(/Séquence/);
    expect(() => provisionalNumber("V", DEVICE, 1.5)).toThrow(/Séquence/);
  });
});
