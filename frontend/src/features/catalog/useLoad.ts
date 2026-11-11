import { useCallback, useEffect, useState } from "react";
import { ApiError, NetworkError } from "../../core/api/errors";

export type Load<T> =
  | { status: "loading" }
  | { status: "ready"; value: T }
  | { status: "offline" }
  | { status: "failed"; error: ApiError };

function asError(value: unknown): Error {
  if (value instanceof Error) return value;
  return new Error(`Erreur non standard (type ${typeof value}) : ${JSON.stringify(value)}`);
}

/**
 * Lecture relancée quand `key` change ; seule la dernière réponse compte. Coupure réseau →
 * « offline », refus de l'API → « failed » (l'écran le dit) ; toute autre erreur est relancée
 * au rendu (fail-fast). `replace` installe la valeur renvoyée par une modification.
 */
export function useLoad<T>(key: string, load: () => Promise<T>) {
  const [state, setState] = useState<{ key: string; load: Load<T> } | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  if (failure !== null) throw asError(failure);

  useEffect(() => {
    let current = true;
    load().then(
      (value) => {
        if (current) setState({ key, load: { status: "ready", value } });
      },
      (error: unknown) => {
        if (!current) return;
        if (error instanceof NetworkError) setState({ key, load: { status: "offline" } });
        else if (error instanceof ApiError) setState({ key, load: { status: "failed", error } });
        else setFailure(error);
      },
    );
    return () => {
      current = false;
    };
    // `load` change à chaque rendu ; la clé décrit seule ce qui doit être relu.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const replace = useCallback(
    (value: T) => {
      // Une réponse arrivée après un changement de clé ne remplace pas la lecture en cours.
      setState((previous) =>
        previous?.key === key ? { key, load: { status: "ready", value } } : previous,
      );
    },
    [key],
  );
  const current: Load<T> = state?.key === key ? state.load : { status: "loading" };
  return [current, replace] as const;
}
