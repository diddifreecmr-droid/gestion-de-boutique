import { useState } from "react";
import { asError } from "../expenses/useLoad";
import { settingsErrorMessage } from "./settingsErrors";

export interface ActionState {
  /** Clé de l'envoi en cours (un élément, « new »…), ou null. */
  busy: string | null;
  /** Dernier refus à afficher, ou null. */
  message: string | null;
  /** Exécute un envoi : `true` s'il a réussi, `false` s'il est refusé (message affiché). */
  run: (key: string, action: () => Promise<void>) => Promise<boolean>;
  clear: () => void;
}

/**
 * Envoi d'une action des réglages : un refus de l'API ou une coupure réseau devient un
 * message à l'écran ; toute autre erreur est relancée au rendu (fail-fast).
 */
export function useAction(): ActionState {
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const run = async (key: string, action: () => Promise<void>): Promise<boolean> => {
    setBusy(key);
    setMessage(null);
    try {
      await action();
      return true;
    } catch (error) {
      try {
        setMessage(settingsErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
      return false;
    } finally {
      setBusy(null);
    }
  };

  return {
    busy,
    message,
    run,
    clear: () => {
      setMessage(null);
    },
  };
}
