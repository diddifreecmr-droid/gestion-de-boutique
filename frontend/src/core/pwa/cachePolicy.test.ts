import { describe, expect, it } from "vitest";
import {
  cacheKeyFor,
  cacheNameFor,
  isFresh,
  manifestUrls,
  MAX_CACHE_AGE_MS,
  NETWORK_TIMEOUT_MS,
  strategyFor,
} from "./cachePolicy";

const ORIGIN = "https://boutique.example";
const get = (path: string, mode = "cors") => ({ url: ORIGIN + path, method: "GET", mode });

describe("politique de cache (specs § 7.3) — stratégie par URL", () => {
  it.each([
    ["/api/v1/me", "bypass"],
    ["/api/v1/auth/refresh", "bypass"],
    ["/api", "bypass"],
    ["/assets/index-B9x_k2Lq.js", "cache-first"],
    ["/assets/index-Dq3mZ0aP.css", "cache-first"],
    ["/index.html", "network-first"],
    ["/", "network-first"],
    ["/manifest.webmanifest", "network-first"],
    ["/icons/icon-192.png", "network-first"],
    ["/assets/logo.svg", "network-first"],
    ["/apiculture", "network-first"],
  ])("%s → %s", (path, strategy) => {
    expect(strategyFor(get(path), ORIGIN)).toBe(strategy);
  });

  it("l'API n'est jamais interceptée, même en navigation", () => {
    expect(strategyFor(get("/api/v1/health", "navigate"), ORIGIN)).toBe("bypass");
  });

  it("une navigation passe par le réseau d'abord", () => {
    expect(strategyFor(get("/s/abc/stock", "navigate"), ORIGIN)).toBe("network-first");
  });

  it("ni les requêtes autres que GET, ni les autres origines", () => {
    expect(strategyFor({ ...get("/index.html"), method: "POST" }, ORIGIN)).toBe("bypass");
    expect(strategyFor(get("/assets/index-B9x_k2Lq.js"), "https://autre.example")).toBe("bypass");
  });

  it("délai réseau de 4 s, expiration à 24 h", () => {
    expect(NETWORK_TIMEOUT_MS).toBe(4000);
    expect(MAX_CACHE_AGE_MS).toBe(86_400_000);
  });
});

describe("politique de cache — clés, fraîcheur, version", () => {
  it("une navigation partage la page d'entrée", () => {
    expect(cacheKeyFor(get("/s/abc/stock", "navigate"))).toBe(`${ORIGIN}/index.html`);
    expect(cacheKeyFor(get("/assets/a-12345678.js"))).toBe(`${ORIGIN}/assets/a-12345678.js`);
  });

  it("une entrée de plus de 24 h, sans date, illisible ou future n'est pas servie", () => {
    const now = 1_000_000_000_000;
    expect(isFresh(String(now - 1000), now)).toBe(true);
    expect(isFresh(String(now - MAX_CACHE_AGE_MS + 1), now)).toBe(true);
    expect(isFresh(String(now - MAX_CACHE_AGE_MS), now)).toBe(false);
    expect(isFresh(null, now)).toBe(false);
    expect(isFresh("hier", now)).toBe(false);
    expect(isFresh(String(now + 60_000), now)).toBe(false);
  });

  it("le nom du cache change avec les révisions et ne dépend pas de l'ordre", () => {
    const a = [{ url: "index.html", revision: "1" }, "assets/x-12345678.js"];
    const b = [{ url: "index.html", revision: "2" }, "assets/x-12345678.js"];
    expect(cacheNameFor(a)).toMatch(/^boutique-app-[0-9a-f]{8}$/);
    expect(cacheNameFor(a)).toBe(cacheNameFor([...a].reverse()));
    expect(cacheNameFor(a)).not.toBe(cacheNameFor(b));
    expect(cacheNameFor([{ url: "a", revision: null }])).toMatch(/^boutique-app-/);
    expect(() => cacheNameFor([])).toThrow("Manifeste du service worker vide");
    expect(manifestUrls(a)).toEqual(["index.html", "assets/x-12345678.js"]);
  });
});
