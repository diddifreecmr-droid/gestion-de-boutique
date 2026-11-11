import { describe, expect, it, vi } from "vitest";
import { createOfflineRights, RIGHTS_KEY } from "./rights";

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: vi.fn((key: string) => data.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      data.set(key, value);
    }),
    removeItem: vi.fn((key: string) => {
      data.delete(key);
    }),
  };
}

describe("droit offline_capture par boutique (TR-26)", () => {
  it("V1 : droit faux noté sans rien écrire sur l'appareil", () => {
    const storage = memoryStorage();
    const rights = createOfflineRights(() => storage);
    rights.note("A", { offline_capture: false });
    expect(rights.isEnabled("A")).toBe(false);
    expect(storage.setItem).not.toHaveBeenCalled();
    expect(storage.removeItem).not.toHaveBeenCalled();
  });

  it("droit ouvert gardé (relu sans réseau), puis retiré", () => {
    const storage = memoryStorage();
    const rights = createOfflineRights(() => storage);
    const listener = vi.fn();
    rights.subscribe(listener);
    rights.note("A", { offline_capture: true });
    rights.note("A", { offline_capture: true });
    expect(listener).toHaveBeenCalledTimes(1);
    expect(createOfflineRights(() => storage).enabledShops()).toEqual(["A"]);
    rights.note("B", { offline_capture: true });
    rights.note("A", { offline_capture: false });
    expect(rights.enabledShops()).toEqual(["B"]);
    rights.note("B", { offline_capture: false });
    expect(storage.removeItem).toHaveBeenCalledWith(RIGHTS_KEY);
  });

  it("contrat rompu : profil sans le droit, stockage mal formé", () => {
    const rights = createOfflineRights(() => memoryStorage());
    expect(() => {
      rights.note("A", {});
    }).toThrow(/offline_capture/);
    const broken = createOfflineRights(() => memoryStorage({ [RIGHTS_KEY]: "[1]" }));
    expect(() => broken.isEnabled("A")).toThrow(/mal formés/);
  });
});
