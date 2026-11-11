/**
 * État du réseau (TR-11, TR-26). Le droit `offline_capture` est **désactivé** en V1 : rien
 * n'est mis en file. Hors connexion, l'écran affiche « Connexion nécessaire » et le
 * formulaire reste rempli pour être renvoyé d'un appui.
 *
 * Hors ligne = le navigateur se dit hors ligne **ou** la dernière requête a échoué pour cause
 * réseau (le Wi-Fi peut être « connecté » sans accès à Internet). La première réponse reçue,
 * ou l'événement `online`, efface l'échec.
 */
import { useSyncExternalStore } from "react";
import { createStore, type Store } from "../state/store";

export interface Connectivity {
  readonly online: boolean;
  reportNetworkFailure: () => void;
  reportResponse: () => void;
  subscribe: (listener: () => void) => () => void;
}

interface Signals {
  browserOnline: boolean;
  requestFailed: boolean;
}

export function createConnectivity(target: Window = window): Connectivity {
  const store: Store<Signals> = createStore<Signals>({
    browserOnline: target.navigator.onLine,
    requestFailed: false,
  });
  const update = (patch: Partial<Signals>) => {
    const current = store.get();
    const next = { ...current, ...patch };
    if (
      next.browserOnline !== current.browserOnline ||
      next.requestFailed !== current.requestFailed
    )
      store.set(next);
  };
  target.addEventListener("online", () => {
    update({ browserOnline: true, requestFailed: false });
  });
  target.addEventListener("offline", () => {
    update({ browserOnline: false });
  });
  return {
    get online() {
      const { browserOnline, requestFailed } = store.get();
      return browserOnline && !requestFailed;
    },
    reportNetworkFailure: () => {
      update({ requestFailed: true });
    },
    reportResponse: () => {
      update({ requestFailed: false });
    },
    subscribe: (listener) => store.subscribe(listener),
  };
}

export function useOnline(connectivity: Connectivity): boolean {
  return useSyncExternalStore(connectivity.subscribe, () => connectivity.online);
}
