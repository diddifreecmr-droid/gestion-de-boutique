import { createContext, useContext, useSyncExternalStore } from "react";
import type { Session } from "../auth/session";
import type { SessionState } from "../auth/sessionState";
import { useOnline } from "../offline/connectivity";
import type { AppServices } from "./createServices";

export const ServicesContext = createContext<AppServices | null>(null);

/** Hors d'un <ServicesProvider>, c'est une erreur de câblage (fail-fast). */
export function useServices(): AppServices {
  const services = useContext(ServicesContext);
  if (services === null) throw new Error("useServices doit être appelé sous un <ServicesProvider>");
  return services;
}

export function useSession(): Session {
  return useServices().session;
}

export function useSessionState(): SessionState {
  const { state } = useSession();
  return useSyncExternalStore(state.subscribe, state.get);
}

/** L'utilisateur connecté ; appelé hors session ouverte, c'est une erreur de garde de route. */
export function useSignedIn() {
  const state = useSessionState();
  if (state.status !== "signedIn") {
    throw new Error(`Écran réservé à une session ouverte (état : ${state.status})`);
  }
  return state.me;
}

export function useIsOnline(): boolean {
  return useOnline(useServices().connectivity);
}
