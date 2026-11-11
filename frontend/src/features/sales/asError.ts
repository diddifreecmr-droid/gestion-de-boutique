/** Garantit une `Error` à relancer au rendu (une valeur non-Error reste lisible). */
export function asError(value: unknown): Error {
  if (value instanceof Error) return value;
  return new Error(`Erreur non standard (type ${typeof value}) : ${JSON.stringify(value)}`);
}
