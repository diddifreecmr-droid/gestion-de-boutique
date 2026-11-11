import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, NetworkError } from "../../core/api/errors";

export type Load<T> =
  | { status: "loading" }
  | { status: "ready"; value: T }
  | { status: "offline" }
  | { status: "failed"; error: ApiError };

/** Garantit une `Error` à relancer au rendu (une valeur non-Error reste lisible). */
export function asError(value: unknown): Error {
  if (value instanceof Error) return value;
  return new Error(`Erreur non standard (type ${typeof value}) : ${JSON.stringify(value)}`);
}

/**
 * Lecture relancée quand `key` change (ou sur `retry`) ; seule la dernière réponse compte.
 * Coupure réseau → « offline », refus de l'API → « failed » (l'écran le dit) ; toute autre
 * erreur est relancée au rendu (fail-fast). `replace` installe la valeur renvoyée par une
 * modification (comptage enregistré, inventaire validé…).
 */
export function useLoad<T>(key: string, load: () => Promise<T>) {
  const latest = useRef(load);
  const [round, setRound] = useState(0);
  const fullKey = `${key}#${String(round)}`;
  const [state, setState] = useState<{ key: string; load: Load<T> } | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  if (failure !== null) throw asError(failure);

  useEffect(() => {
    latest.current = load;
  });

  useEffect(() => {
    let current = true;
    latest.current().then(
      (value) => {
        if (current) setState({ key: fullKey, load: { status: "ready", value } });
      },
      (error: unknown) => {
        if (!current) return;
        if (error instanceof NetworkError) setState({ key: fullKey, load: { status: "offline" } });
        else if (error instanceof ApiError) {
          setState({ key: fullKey, load: { status: "failed", error } });
        } else setFailure(error);
      },
    );
    return () => {
      current = false;
    };
  }, [fullKey]);

  const replace = useCallback(
    (value: T) => {
      setState((previous) =>
        previous?.key === fullKey ? { key: fullKey, load: { status: "ready", value } } : previous,
      );
    },
    [fullKey],
  );
  const retry = useCallback(() => {
    setRound((n) => n + 1);
  }, []);
  const current: Load<T> = state?.key === fullKey ? state.load : { status: "loading" };
  return { load: current, replace, retry };
}
