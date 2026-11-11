import { useEffect, useState } from "react";
import { NetworkError } from "../../core/api/errors";
import { asError } from "./asError";

export type Lookup<T> =
  { status: "loading" } | { status: "ready"; value: T } | { status: "offline" };

/**
 * Lecture asynchrone relancée quand `key` change (recherche dès la 1re lettre). Seule la
 * dernière réponse compte. Coupure réseau → « offline » (l'écran le dit) ; toute autre
 * erreur est relancée au rendu (fail-fast), jamais avalée.
 */
export function useLookup<T>(key: string, load: () => Promise<T>): Lookup<T> {
  const [state, setState] = useState<{ key: string; lookup: Lookup<T> } | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  if (failure !== null) throw asError(failure);

  useEffect(() => {
    let current = true;
    load().then(
      (value) => {
        if (current) setState({ key, lookup: { status: "ready", value } });
      },
      (error: unknown) => {
        if (!current) return;
        if (error instanceof NetworkError) setState({ key, lookup: { status: "offline" } });
        else setFailure(error);
      },
    );
    return () => {
      current = false;
    };
    // `load` change à chaque rendu ; la clé décrit seule ce qui doit être relu.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return state?.key === key ? state.lookup : { status: "loading" };
}
