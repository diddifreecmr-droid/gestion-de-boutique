import { createContext, useContext, useState } from "react";
import type { ReportingGateway } from "../../core/gateways/reportingContract";
import { useIsOnline } from "../../core/services/servicesContext";
import { useLoad, type Loaded } from "../expenses/useLoad";

/** Dépendances des écrans du tableau de bord : passerelle et horloge (remplaçables en test). */
export interface ReportingDeps {
  gateway: ReportingGateway;
  now: () => Date;
}

export const ReportingContext = createContext<ReportingDeps | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function useReporting(): ReportingDeps {
  const deps = useContext(ReportingContext);
  if (deps === null) throw new Error("useReporting doit être appelé sous un ReportingContext");
  return deps;
}

export interface Figures<T> {
  loaded: Loaded<T>;
  /** « Réessayer » : relit le serveur. */
  retry: () => void;
}

/**
 * Lecture de chiffres (RG-T25) : hors connexion, l'écran ne montre **jamais** de chiffre, même
 * déjà lu — l'état passe à « offline » ; le retour du réseau relance la lecture. Une coupure
 * pendant la lecture donne aussi « offline » ; toute autre erreur est relancée (fail-fast).
 */
export function useFigures<T>(key: string, load: () => Promise<T>): Figures<T> {
  const online = useIsOnline();
  const [attempt, setAttempt] = useState(0);
  const loaded = useLoad(`${key}|${String(online)}|${String(attempt)}`, load);
  return {
    loaded: online ? loaded : { status: "offline" },
    retry: () => {
      setAttempt((current) => current + 1);
    },
  };
}
