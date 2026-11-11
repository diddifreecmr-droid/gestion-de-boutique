import { useState } from "react";
import { stockFailure, type StockFailure } from "./stockErrors";

/**
 * Envoi d'une écriture du stock : un seul envoi à la fois, refus traduit en `failure`
 * (affiché par l'écran). Une erreur imprévue est relancée au rendu (fail-fast).
 */
export function useStockSubmit(locationName = "") {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<StockFailure | null>(null);
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
        setFailure(stockFailure(error, locationName));
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
