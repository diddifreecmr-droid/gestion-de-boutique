/**
 * Petit client `fetch` typé par le contrat généré (specs § 6.1, § 7.2).
 *
 * - URL : `base` (VITE_API_BASE, ex. « /api ») + chemin du contrat sans son préfixe « /api ».
 * - En-têtes : `X-Device-Id` toujours, `Authorization: Bearer` si un jeton est fourni.
 * - `credentials: "include"` : le cookie de rafraîchissement (httpOnly) part avec `/auth/*`.
 * - Erreur : `ApiError` (enveloppe lue) ou `NetworkError` (serveur injoignable). Rien d'avalé.
 */
import { ApiError, NetworkError, parseErrorEnvelope } from "./errors";
import type { paths } from "./schema.gen";

/** Préfixe des chemins du contrat, remplacé par `base` à l'appel. */
export const CONTRACT_PREFIX = "/api";

type Method = "get" | "post";
type PathsWith<M extends Method> = {
  [P in keyof paths]: paths[P][M] extends { responses: unknown } ? P : never;
}[keyof paths];
type Operation<P extends keyof paths, M extends Method> = Extract<
  paths[P][M],
  { responses: unknown }
>;
type JsonContent<T> = T extends { content: { "application/json": infer J } } ? J : undefined;
type Responses<P extends keyof paths, M extends Method> = Operation<P, M>["responses"];

/** Corps de la réponse 200 (ou `undefined` pour une 204). */
export type ResponseOf<P extends keyof paths, M extends Method> = 200 extends keyof Responses<P, M>
  ? JsonContent<Responses<P, M>[200]>
  : undefined;
/** Corps JSON attendu par l'opération (`undefined` si elle n'en prend pas). */
export type BodyOf<P extends keyof paths, M extends Method> =
  Operation<P, M> extends { requestBody: infer B } ? JsonContent<NonNullable<B>> : undefined;

export interface CallOptions<B> {
  body?: B;
  /** Jeton d'accès (gardé en mémoire par la session, jamais persisté). */
  token?: string;
}

export interface ClientHooks {
  /** Une réponse HTTP est arrivée : le réseau fonctionne. */
  onResponse?: () => void;
  /** La requête n'a pas pu partir ou aboutir pour cause réseau. */
  onNetworkFailure?: (error: NetworkError) => void;
}

export interface ApiClientOptions extends ClientHooks {
  base: string;
  deviceId: () => string;
  fetch?: typeof fetch;
}

export interface ApiClient {
  get<P extends PathsWith<"get">>(
    path: P,
    options?: CallOptions<never>,
  ): Promise<ResponseOf<P, "get">>;
  post<P extends PathsWith<"post">>(
    path: P,
    options?: CallOptions<BodyOf<P, "post">>,
  ): Promise<ResponseOf<P, "post">>;
}

export function resolveUrl(base: string, path: string): string {
  if (base.endsWith("/"))
    throw new Error(`VITE_API_BASE ne doit pas finir par « / » : « ${base} »`);
  if (!path.startsWith(`${CONTRACT_PREFIX}/`)) {
    throw new Error(`Chemin hors contrat : « ${path} » (attendu ${CONTRACT_PREFIX}/…)`);
  }
  return base + path.slice(CONTRACT_PREFIX.length);
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text === "") return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch (cause) {
    if (!response.ok) return undefined; // l'enveloppe absente est signalée par parseErrorEnvelope
    throw new ApiError(response.status, "INVALID_RESPONSE", "Réponse illisible du serveur", {
      cause: String(cause),
    });
  }
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const fetchImpl = options.fetch ?? globalThis.fetch.bind(globalThis);

  async function call(method: Method, path: string, init: CallOptions<unknown>): Promise<unknown> {
    const headers = new Headers({ Accept: "application/json", "X-Device-Id": options.deviceId() });
    if (init.token !== undefined) headers.set("Authorization", `Bearer ${init.token}`);
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    let response: Response;
    try {
      response = await fetchImpl(resolveUrl(options.base, path), {
        method: method.toUpperCase(),
        headers,
        credentials: "include",
        cache: "no-store",
        ...(init.body === undefined ? {} : { body: JSON.stringify(init.body) }),
      });
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
      const error = new NetworkError("Serveur injoignable : connexion nécessaire", { cause });
      options.onNetworkFailure?.(error);
      throw error;
    }
    options.onResponse?.();
    const body = await readJson(response);
    if (!response.ok) throw parseErrorEnvelope(response.status, body);
    return body;
  }

  return {
    get: (path, init = {}) => call("get", path, init) as never,
    post: (path, init = {}) => call("post", path, init) as never,
  };
}
