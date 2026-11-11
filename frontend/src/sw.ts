/// <reference lib="webworker" />
/**
 * Service worker (specs § 7.3) : applique `core/pwa/cachePolicy.ts`.
 *
 * - `/api/*` n'est jamais intercepté ; pages et manifest en réseau d'abord (4 s) ; fichiers
 *   à empreinte en cache d'abord ; aucune entrée servie après 24 h.
 * - Mise à jour au prochain lancement : pas de `skipWaiting()` automatique. La nouvelle version
 *   attend ; elle prend la main quand tous les onglets sont fermés, ou quand l'utilisateur
 *   appuie sur « Mettre à jour » (message `SKIP_WAITING`).
 * - Hors-ligne désactivé (TR-26) : aucune file d'envoi ici.
 */
import {
  CACHED_AT_HEADER,
  cacheKeyFor,
  cacheNameFor,
  isFresh,
  manifestUrls,
  NETWORK_TIMEOUT_MS,
  strategyFor,
  type ManifestEntry,
} from "./core/pwa/cachePolicy";

declare const self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: (ManifestEntry | string)[];
};

const MANIFEST = self.__WB_MANIFEST;
const CACHE = cacheNameFor(MANIFEST);

/** Copie datée d'une réponse réussie de même origine (les autres ne sont pas gardées). */
async function store(key: string, response: Response): Promise<void> {
  if (!response.ok || response.type !== "basic") return;
  const headers = new Headers(response.headers);
  headers.set(CACHED_AT_HEADER, String(Date.now()));
  const body = await response.clone().blob();
  const cache = await caches.open(CACHE);
  await cache.put(key, new Response(body, { status: response.status, headers }));
}

async function freshCopy(key: string): Promise<Response | undefined> {
  const cached = await (await caches.open(CACHE)).match(key);
  if (cached === undefined) return undefined;
  return isFresh(cached.headers.get(CACHED_AT_HEADER), Date.now()) ? cached : undefined;
}

async function networkFirst(request: Request, key: string): Promise<Response> {
  const network = fetch(request).then(async (response) => {
    await store(key, response);
    return response;
  });
  network.catch((error: unknown) => {
    console.warn("Service worker : réseau indisponible pour", key, error);
  });
  const timeout = new Promise<"timeout">((resolve) => {
    setTimeout(() => {
      resolve("timeout");
    }, NETWORK_TIMEOUT_MS);
  });
  try {
    const first = await Promise.race([network, timeout]);
    if (first !== "timeout") return first;
  } catch (error) {
    const cached = await freshCopy(key);
    if (cached !== undefined) return cached;
    throw error;
  }
  // Pas de réponse en 4 s : la copie récente si elle existe, sinon on attend le réseau.
  return (await freshCopy(key)) ?? network;
}

async function cacheFirst(request: Request, key: string): Promise<Response> {
  const cached = await freshCopy(key);
  if (cached !== undefined) return cached;
  const response = await fetch(request);
  await store(key, response);
  return response;
}

self.addEventListener("install", (event) => {
  // Fichiers du build mis en cache à l'avance ; un échec fait échouer l'installation.
  event.waitUntil(
    (async () => {
      const urls = manifestUrls(MANIFEST).map((url) => new URL(url, self.registration.scope).href);
      await Promise.all(
        urls.map(async (url) => {
          const response = await fetch(url, { cache: "reload" });
          if (!response.ok)
            throw new Error(`Préchargement refusé : ${url} (${String(response.status)})`);
          await store(url, response);
        }),
      );
    })(),
  );
});

self.addEventListener("activate", (event) => {
  // Supprime les caches des versions précédentes (dont l'ancien précache Workbox de T03).
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(names.filter((name) => name !== CACHE).map((name) => caches.delete(name)));
    })(),
  );
});

self.addEventListener("message", (event) => {
  const data: unknown = event.data;
  if (typeof data === "object" && data !== null && "type" in data && data.type === "SKIP_WAITING") {
    event.waitUntil(self.skipWaiting());
  }
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const strategy = strategyFor(request, self.location.origin);
  if (strategy === "bypass") return; // le navigateur traite la requête lui-même
  const key = cacheKeyFor(request);
  event.respondWith(
    strategy === "cache-first" ? cacheFirst(request, key) : networkFirst(request, key),
  );
});
