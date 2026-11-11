/**
 * Une seule exécution à la fois : les appels concurrents reçoivent la **même** promesse.
 * Sert au rafraîchissement du jeton : deux refresh simultanés avec le même cookie feraient
 * réutiliser un jeton déjà tourné, ce que le serveur traite comme un vol (SESSION_REVOKED).
 */
export function singleFlight<T>(task: () => Promise<T>): () => Promise<T> {
  let inFlight: Promise<T> | null = null;
  return () => {
    inFlight ??= task().finally(() => {
      inFlight = null;
    });
    return inFlight;
  };
}
