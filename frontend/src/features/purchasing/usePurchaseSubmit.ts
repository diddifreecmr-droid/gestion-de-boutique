import { useState } from "react";
import { asError } from "../expenses/useLoad";
import { purchaseErrorMessage } from "./purchaseErrors";
import { priceGapsOf, type PriceGap } from "./priceGap";

/**
 * Envoi d'une saisie d'achat : un seul envoi à la fois ; l'avertissement d'écart de prix ouvre
 * une confirmation (`gaps`) au lieu d'un message ; tout autre refus devient `message` et la
 * saisie est conservée. Une erreur imprévue est relancée au rendu (fail-fast).
 */
export function usePurchaseSubmit(send: (confirmPriceGap: boolean) => Promise<void>) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [gaps, setGaps] = useState<PriceGap[] | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const run = async (confirmPriceGap: boolean) => {
    if (pending) return;
    setGaps(null);
    setMessage(null);
    setPending(true);
    try {
      await send(confirmPriceGap);
    } catch (error) {
      try {
        const found = priceGapsOf(error);
        if (found === null) setMessage(purchaseErrorMessage(error));
        else setGaps(found);
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setPending(false);
    }
  };

  return {
    pending,
    message,
    gaps,
    run,
    /** Message posé par l'écran (champs à corriger). */
    say: setMessage,
    dismissGaps: () => {
      setGaps(null);
    },
  };
}
