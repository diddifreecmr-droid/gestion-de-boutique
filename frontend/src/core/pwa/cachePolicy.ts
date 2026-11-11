/**
 * Politique de cache (specs § 7.3, décision du 11/11/2026), en logique pure : le service
 * worker (src/sw.ts) ne fait qu'appliquer ces règles. Aucune API DOM ni Worker ici.
 *
 * | Ressource                         | Stratégie                                  |
 * | --------------------------------- | ------------------------------------------ |
 * | `/api/*`, autre origine, non-GET  | jamais interceptée (`bypass`)              |
 * | page d'entrée, manifest, le reste | réseau d'abord, cache si pas de réponse 4 s |
 * | fichiers à empreinte (`/assets/`) | cache d'abord                              |
 * | toute entrée du cache             | expire au bout de 24 h au plus             |
 */

export type Strategy = "bypass" | "network-first" | "cache-first";

export const NETWORK_TIMEOUT_MS = 4_000;
export const MAX_CACHE_AGE_MS = 24 * 60 * 60 * 1_000;
/** En-tête ajouté à la copie mise en cache : instant d'enregistrement (ms depuis l'époque). */
export const CACHED_AT_HEADER = "x-sw-cached-at";
/** Toute navigation est servie par la page d'entrée de l'application (SPA). */
export const APP_SHELL_URL = "/index.html";
export const CACHE_PREFIX = "boutique-app-";

/** Empreinte de contenu posée par Vite : `/assets/index-B9x_k2Lq.js`. */
const FINGERPRINTED = /^\/assets\/.+-[A-Za-z0-9_-]{8,}\.[a-z0-9]+$/;

export interface RequestFacts {
  url: string;
  method: string;
  mode: string;
}

export function strategyFor(request: RequestFacts, origin: string): Strategy {
  if (request.method !== "GET") return "bypass";
  const url = new URL(request.url);
  if (url.origin !== origin) return "bypass";
  if (url.pathname === "/api" || url.pathname.startsWith("/api/")) return "bypass";
  if (request.mode !== "navigate" && FINGERPRINTED.test(url.pathname)) return "cache-first";
  return "network-first";
}

/** Clé de cache : une navigation (`/s/…/stock`) partage la page d'entrée. */
export function cacheKeyFor(request: RequestFacts): string {
  if (request.mode === "navigate") return new URL(APP_SHELL_URL, request.url).href;
  return request.url;
}

/** Une entrée sans date, à date illisible ou future, ou de plus de 24 h, n'est pas servie. */
export function isFresh(cachedAt: string | null, now: number): boolean {
  if (cachedAt === null) return false;
  const stamp = Number(cachedAt);
  if (!Number.isSafeInteger(stamp)) return false;
  const age = now - stamp;
  return age >= 0 && age < MAX_CACHE_AGE_MS;
}

export interface ManifestEntry {
  url: string;
  revision: string | null;
}

/** Nom du cache propre à une version publiée (dérivé des révisions du manifeste). */
export function cacheNameFor(entries: readonly (ManifestEntry | string)[]): string {
  if (entries.length === 0) throw new Error("Manifeste du service worker vide");
  const text = entries
    .map((entry) => (typeof entry === "string" ? entry : `${entry.url}@${entry.revision ?? ""}`))
    .sort()
    .join("|");
  let hash = 0x811c9dc5; // FNV-1a 32 bits : stable, suffisant pour distinguer deux versions
  for (let index = 0; index < text.length; index++) {
    hash = Math.imul(hash ^ text.charCodeAt(index), 0x01000193) >>> 0;
  }
  return `${CACHE_PREFIX}${hash.toString(16).padStart(8, "0")}`;
}

export function manifestUrls(entries: readonly (ManifestEntry | string)[]): string[] {
  return entries.map((entry) => (typeof entry === "string" ? entry : entry.url));
}
