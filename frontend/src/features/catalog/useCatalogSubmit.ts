import { useState } from "react";
import { submitFailure, type SubmitFailure } from "./catalogErrors";

/**
 * Envoi d'une modification du catalogue : un seul envoi à la fois, refus traduit en
 * `failure` (affiché par l'écran). Une erreur imprévue est relancée au rendu (fail-fast).
 */
export function useCatalogSubmit() {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<SubmitFailure | null>(null);
  const [crash, setCrash] = useState<{ error: unknown } | null>(null);
  if (crash !== null) throw crash.error;

  async function run<T>(action: () => Promise<T>, onDone: (value: T) => void): Promise<void> {
    if (pending) return;
    setPending(true);
    setFailure(null);
    try {
      const value = await action();
      setPending(false);
      onDone(value);
    } catch (error) {
      setPending(false);
      try {
        setFailure(submitFailure(error));
      } catch (unexpected) {
        setCrash({ error: unexpected });
      }
    }
  }

  return {
    pending,
    failure,
    run,
    clear: () => {
      setFailure(null);
    },
  };
}
