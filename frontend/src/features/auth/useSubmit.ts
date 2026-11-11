import { useState } from "react";

/**
 * Envoi d'un formulaire : `pending` bloque le double appui ; l'erreur est remise à l'écran
 * par `onError`, qui relance ce qu'il ne sait pas traiter. La saisie n'est jamais effacée.
 */
export function useSubmit(onError: (error: unknown) => void) {
  const [pending, setPending] = useState(false);
  const run = async (action: () => Promise<void>) => {
    if (pending) return;
    setPending(true);
    try {
      await action();
    } catch (error) {
      onError(error);
    } finally {
      setPending(false);
    }
  };
  return { pending, run };
}
