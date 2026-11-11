import { useEffect, useRef, useState } from "react";
import { NetworkError } from "../../core/api/errors";

export type Loaded<T> =
  { status: "loading" } | { status: "ready"; value: T } | { status: "offline" };

/** Garantit une `Error` à relancer au rendu (une valeur non-Error reste lisible). */
export function asError(value: unknown): Error {
  if (value instanceof Error) return value;
  return new Error(`Erreur non standard (type ${typeof value}) : ${JSON.stringify(value)}`);
}

/**
 * Lecture asynchrone relancée quand `key` change ; seule la dernière réponse compte.
 * Coupure réseau → « offline » (l'écran le dit, avec « Réessayer ») ; toute autre erreur est
 * relancée au rendu (fail-fast), jamais avalée.
 */
export function useLoad<T>(key: string, load: () => Promise<T>): Loaded<T> {
  const latest = useRef(load);
  const [state, setState] = useState<{ key: string; loaded: Loaded<T> } | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  if (failure !== null) throw asError(failure);

  useEffect(() => {
    latest.current = load;
  });

  useEffect(() => {
    let current = true;
    latest.current().then(
      (value) => {
        if (current) setState({ key, loaded: { status: "ready", value } });
      },
      (error: unknown) => {
        if (!current) return;
        if (error instanceof NetworkError) setState({ key, loaded: { status: "offline" } });
        else setFailure(error);
      },
    );
    return () => {
      current = false;
    };
  }, [key]);

  return state?.key === key ? state.loaded : { status: "loading" };
}
