import { useState } from "react";
import { asError } from "../expenses/useLoad";
import { receivableErrorMessage } from "./receivableErrors";

/**
 * Lance une action (versement, rappel, mise en perte…) : une seule à la fois, message clair
 * en cas de refus du serveur ou de coupure. Toute autre erreur est relancée au rendu.
 */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  /** Vrai si l'action a abouti. */
  const run = async (action: () => Promise<void>): Promise<boolean> => {
    if (busy) return false;
    setBusy(true);
    setMessage(null);
    try {
      await action();
      return true;
    } catch (error) {
      try {
        setMessage(receivableErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, message, setMessage, run };
}
