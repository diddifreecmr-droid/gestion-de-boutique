/**
 * Nouvelle version de l'application (specs § 7.3) : vérification à l'ouverture puis toutes
 * les 30 min ; quand une version attend, la bannière « Nouvelle version disponible » s'affiche.
 * Rien n'est rechargé sans l'appui de l'utilisateur sur « Mettre à jour ».
 */
export const UPDATE_CHECK_INTERVAL_MS = 30 * 60 * 1_000;
export const SW_URL = "/sw.js";

export interface UpdateWatcherDeps {
  container: ServiceWorkerContainer;
  /** Une version installée attend : on la propose. */
  onUpdateReady: (worker: ServiceWorker) => void;
  /** Échec d'une vérification (souvent hors ligne) : signalé, la prochaine réessaiera. */
  onCheckFailed: (error: unknown) => void;
  setInterval?: (handler: () => void, ms: number) => number;
}

/** Inscrit le service worker et surveille les mises à jour ; renvoie de quoi arrêter. */
export async function watchForUpdates(deps: UpdateWatcherDeps): Promise<() => void> {
  const { container, onUpdateReady, onCheckFailed } = deps;
  const every = deps.setInterval ?? ((handler, ms) => window.setInterval(handler, ms));
  const registration = await container.register(SW_URL, { scope: "/", updateViaCache: "none" });

  // Première installation (aucun contrôleur) : rien à proposer, la version est déjà la bonne.
  const offer = (worker: ServiceWorker | null) => {
    if (worker !== null && container.controller !== null) onUpdateReady(worker);
  };
  registration.addEventListener("updatefound", () => {
    const installing = registration.installing;
    installing?.addEventListener("statechange", () => {
      if (installing.state === "installed") offer(installing);
    });
  });
  offer(registration.waiting);

  const check = () => {
    registration.update().catch(onCheckFailed);
  };
  check();
  const timer = every(check, UPDATE_CHECK_INTERVAL_MS);
  return () => {
    window.clearInterval(timer);
  };
}

/** « Mettre à jour » : la version en attente prend la main, puis la page se recharge. */
export function applyUpdate(
  worker: ServiceWorker,
  container: ServiceWorkerContainer,
  reload: () => void,
): void {
  container.addEventListener("controllerchange", reload, { once: true });
  worker.postMessage({ type: "SKIP_WAITING" });
}
