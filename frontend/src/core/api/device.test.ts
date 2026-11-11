import { describe, expect, it } from "vitest";
import { DEVICE_ID_KEY, DeviceIdError, deviceLabel, readDeviceId } from "./device";
import { isUuidV7, uuidV7 } from "./uuidv7";

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value);
    },
    data,
  };
}

describe("uuidV7", () => {
  it("produit un UUIDv7 (RFC 9562) dont les 48 premiers bits sont l'horodatage", () => {
    const value = uuidV7(0x0189_0a5d_ac96);
    expect(isUuidV7(value)).toBe(true);
    expect(value.startsWith("01890a5d-ac96-7")).toBe(true);
    expect(uuidV7()).not.toBe(uuidV7());
  });

  it("refuse un horodatage hors de 48 bits", () => {
    expect(() => uuidV7(-1)).toThrow(RangeError);
    expect(() => uuidV7(2 ** 48)).toThrow("Horodatage UUIDv7 invalide");
  });

  it("reconnaît seulement la version 7", () => {
    expect(isUuidV7("550e8400-e29b-41d4-a716-446655440000")).toBe(false);
  });
});

describe("readDeviceId", () => {
  it("crée l'identifiant une fois puis le réutilise", () => {
    const storage = memoryStorage();
    const first = readDeviceId(() => storage);
    expect(isUuidV7(first)).toBe(true);
    expect(storage.data.get(DEVICE_ID_KEY)).toBe(first);
    expect(readDeviceId(() => storage)).toBe(first);
  });

  it("remplace une valeur enregistrée illisible", () => {
    const storage = memoryStorage({ [DEVICE_ID_KEY]: "abimé" });
    expect(isUuidV7(readDeviceId(() => storage))).toBe(true);
  });

  it("utilise localStorage par défaut", () => {
    window.localStorage.removeItem(DEVICE_ID_KEY);
    const value = readDeviceId();
    expect(window.localStorage.getItem(DEVICE_ID_KEY)).toBe(value);
  });

  it("lève DeviceIdError si le stockage est inaccessible (lecture ou écriture)", () => {
    const blocked = () => {
      throw new DOMException("refusé", "SecurityError");
    };
    expect(() => readDeviceId(blocked)).toThrow(DeviceIdError);
    const readOnly = {
      getItem: () => null,
      setItem: () => {
        throw new DOMException("plein", "QuotaExceededError");
      },
    };
    expect(() => readDeviceId(() => readOnly)).toThrow("identifiant non enregistré");
  });
});

describe("deviceLabel", () => {
  it.each([
    [
      "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131.0 Mobile Safari/537.36",
      "Android — Chrome",
    ],
    [
      "Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36 Edg/131.0",
      "Windows — Edge",
    ],
    [
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Safari/604.1",
      "iPhone — Safari",
    ],
    ["curl/8.0", "Appareil — Navigateur"],
  ])("%s → %s", (ua, label) => {
    expect(deviceLabel(ua)).toBe(label);
  });
});
