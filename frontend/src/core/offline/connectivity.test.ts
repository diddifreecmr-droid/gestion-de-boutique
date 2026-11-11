import { describe, expect, it, vi } from "vitest";
import { createConnectivity } from "./connectivity";

function fakeWindow(onLine: boolean) {
  const target = new EventTarget() as Window;
  Object.defineProperty(target, "navigator", { value: { onLine } });
  return target;
}

describe("connectivité", () => {
  it("suit navigator.onLine et les événements online / offline", () => {
    const target = fakeWindow(false);
    const connectivity = createConnectivity(target);
    const listener = vi.fn();
    connectivity.subscribe(listener);
    expect(connectivity.online).toBe(false);
    target.dispatchEvent(new Event("online"));
    expect(connectivity.online).toBe(true);
    target.dispatchEvent(new Event("offline"));
    expect(connectivity.online).toBe(false);
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("un échec réseau d'une requête passe hors ligne jusqu'à la prochaine réponse", () => {
    const connectivity = createConnectivity(fakeWindow(true));
    const listener = vi.fn();
    const unsubscribe = connectivity.subscribe(listener);
    connectivity.reportNetworkFailure();
    expect(connectivity.online).toBe(false);
    connectivity.reportNetworkFailure();
    connectivity.reportResponse();
    expect(connectivity.online).toBe(true);
    expect(listener).toHaveBeenCalledTimes(2);
    unsubscribe();
    connectivity.reportNetworkFailure();
    expect(listener).toHaveBeenCalledTimes(2);
  });
});
