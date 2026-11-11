/** État « nouvelle version disponible », partagé par la bannière. */
import { useSyncExternalStore } from "react";
import { createStore } from "../state/store";
import { applyUpdate, watchForUpdates } from "./updates";

const waitingWorker = createStore<ServiceWorker | null>(null);

/** Production uniquement : inscrit le service worker et surveille les mises à jour. */
export function startUpdateWatcher(container: ServiceWorkerContainer): Promise<() => void> {
  return watchForUpdates({
    container,
    onUpdateReady: (worker) => {
      waitingWorker.set(worker);
    },
    onCheckFailed: (error) => {
      console.warn("Vérification de nouvelle version impossible (nouvel essai dans 30 min)", error);
    },
  });
}

export function useUpdateReady(): boolean {
  return useSyncExternalStore(waitingWorker.subscribe, () => waitingWorker.get() !== null);
}

export function installWaitingUpdate(): void {
  const worker = waitingWorker.get();
  if (worker === null) throw new Error("Aucune nouvelle version en attente");
  applyUpdate(worker, navigator.serviceWorker, () => {
    window.location.reload();
  });
}

/** Tests uniquement : simule une version en attente. */
export const updateStoreForTests = waitingWorker;
