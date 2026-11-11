/**
 * « Recharger la dernière version » (specs § 7.3) : vide les caches, désinscrit le service
 * worker et recharge tout depuis le serveur. Une étape qui échoue fait échouer l'ensemble.
 */
export interface ReloadDeps {
  /** `undefined` hors contexte sécurisé : il n'y a alors rien à vider. */
  caches: CacheStorage | undefined;
  serviceWorker: ServiceWorkerContainer | undefined;
  reload: () => void;
}

export function browserReloadDeps(): ReloadDeps {
  return {
    caches: "caches" in window ? window.caches : undefined,
    serviceWorker: "serviceWorker" in navigator ? navigator.serviceWorker : undefined,
    reload: () => {
      window.location.reload();
    },
  };
}

export async function reloadLatestVersion(deps: ReloadDeps = browserReloadDeps()): Promise<void> {
  if (deps.caches !== undefined) {
    const store = deps.caches;
    const names = await store.keys();
    await Promise.all(names.map((name) => store.delete(name)));
  }
  if (deps.serviceWorker !== undefined) {
    const registrations = await deps.serviceWorker.getRegistrations();
    const results = await Promise.all(
      registrations.map((registration) => registration.unregister()),
    );
    if (results.includes(false)) throw new Error("Le service worker n'a pas pu être désinscrit");
  }
  deps.reload();
}
