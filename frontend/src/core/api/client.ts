/**
 * Petit client `fetch` typé par le contrat généré (specs § 6.1, § 7.2).
 *
 * - URL : `base` (VITE_API_BASE, ex. « /api ») + chemin du contrat sans son préfixe « /api ».
 * - En-têtes : `X-Device-Id` toujours, `Authorization: Bearer` si un jeton est fourni, et
 *   ceux de l'appel (`headers`, ex. `X-Captured-At`).
 * - `credentials: "include"` : le cookie de rafraîchissement (httpOnly) part avec `/auth/*`.
 * - Erreur : `ApiError` (enveloppe lue) ou `NetworkError` (serveur injoignable). Rien d'avalé.
 */
import { ApiError, NetworkError, parseErrorEnvelope } from "./errors";
import { fillPath, queryString, type PathParams, type QueryParams } from "./pathParams";
import type { paths } from "./schema.gen";

/** Préfixe des chemins du contrat, remplacé par `base` à l'appel. */
export const CONTRACT_PREFIX = "/api";

type Method = "get" | "post" | "patch" | "put";
type PathsWith<M extends Method> = {
  [P in keyof paths]: paths[P][M] extends { responses: unknown } ? P : never;
}[keyof paths];
type Operation<P extends keyof paths, M extends Method> = Extract<
  paths[P][M],
  { responses: unknown }
>;
type JsonContent<T> = T extends { content: { "application/json": infer J } } ? J : undefined;
type Responses<P extends keyof paths, M extends Method> = Operation<P, M>["responses"];

/** Corps de la réponse 200 (201 pour une création ; `undefined` pour une 204). */
export type ResponseOf<P extends keyof paths, M extends Method> = 200 extends keyof Responses<P, M>
  ? JsonContent<Responses<P, M>[200]>
  : 201 extends keyof Responses<P, M>
    ? JsonContent<Responses<P, M>[201]>
    : undefined;
/** Corps JSON attendu par l'opération (`undefined` si elle n'en prend pas). */
export type BodyOf<P extends keyof paths, M extends Method> =
  Operation<P, M> extends { requestBody: infer B } ? JsonContent<NonNullable<B>> : undefined;

export interface CallOptions<B> {
  body?: B;
  /** Jeton d'accès (gardé en mémoire par la session, jamais persisté). */
  token?: string;
  /** Valeurs des `{nom}` du chemin (`shop_id`, `article_id`…). */
  params?: PathParams;
  /** Paramètres `?clé=valeur` (omis si `null` ou `undefined`). */
  query?: QueryParams;
  /**
   * En-têtes propres à l'appel (`X-Captured-At` d'une vente). Ceux que le client pose
   * lui-même (`Accept`, `Authorization`, `Content-Type`, `X-Device-Id`) sont refusés.
   */
  headers?: Readonly<Record<string, string>>;
}

/** En-têtes réservés au client : un appel ne peut pas les remplacer (fail-fast). */
const RESERVED_HEADERS = ["accept", "authorization", "content-type", "x-device-id"];

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
  patch<P extends PathsWith<"patch">>(
    path: P,
    options?: CallOptions<BodyOf<P, "patch">>,
  ): Promise<ResponseOf<P, "patch">>;
  put<P extends PathsWith<"put">>(
    path: P,
    options?: CallOptions<BodyOf<P, "put">>,
  ): Promise<ResponseOf<P, "put">>;
  /** Envoi `multipart/form-data` (pièces jointes) : le navigateur pose l'en-tête et la borne. */
  postForm<P extends PathsWith<"post">>(
    path: P,
    options: CallOptions<never> & { form: FormData },
  ): Promise<ResponseOf<P, "post">>;
  /** Fichier binaire (modèle `.xlsx`) : contenu et nom donné par `Content-Disposition`. */
  getFile(path: PathsWith<"get">, options?: CallOptions<never>): Promise<FetchedFile>;
  /** URL navigateur d'un chemin du contrat (ex. lien signé d'une pièce jointe). */
  href(path: string): string;
}

export interface FetchedFile {
  blob: Blob;
  /** Nom proposé par le serveur ; `null` sans en-tête `Content-Disposition` lisible. */
  fileName: string | null;
}

/** `attachment; filename="modele.xlsx"` → `modele.xlsx`. */
export function dispositionName(header: string | null): string | null {
  const found = header === null ? null : /filename="?([^";]+)"?/i.exec(header);
  return found?.[1] ?? null;
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

  async function call(
    method: Method,
    path: string,
    init: CallOptions<unknown> & { form?: FormData; file?: true },
  ): Promise<unknown> {
    const accept = init.file === true ? "*/*" : "application/json";
    const headers = new Headers({ Accept: accept, "X-Device-Id": options.deviceId() });
    if (init.token !== undefined) headers.set("Authorization", `Bearer ${init.token}`);
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    const payload = init.form ?? (init.body === undefined ? undefined : JSON.stringify(init.body));
    for (const [name, value] of Object.entries(init.headers ?? {})) {
      if (RESERVED_HEADERS.includes(name.toLowerCase())) {
        throw new Error(`En-tête « ${name} » réservé au client API`);
      }
      headers.set(name, value);
    }
    // Hors du `try` : un chemin mal câblé est une erreur de code, pas une coupure réseau.
    const url = resolveUrl(options.base, fillPath(path, init.params)) + queryString(init.query);
    let response: Response;
    try {
      response = await fetchImpl(url, {
        method: method.toUpperCase(),
        headers,
        credentials: "include",
        cache: "no-store",
        ...(payload === undefined ? {} : { body: payload }),
      });
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
      const error = new NetworkError("Serveur injoignable : connexion nécessaire", { cause });
      options.onNetworkFailure?.(error);
      throw error;
    }
    options.onResponse?.();
    if (init.file === true && response.ok) {
      const fileName = dispositionName(response.headers.get("Content-Disposition"));
      return { blob: await response.blob(), fileName } satisfies FetchedFile;
    }
    const body = await readJson(response);
    if (!response.ok) throw parseErrorEnvelope(response.status, body);
    return body;
  }

  return {
    get: (path, init = {}) => call("get", path, init) as never,
    post: (path, init = {}) => call("post", path, init) as never,
    patch: (path, init = {}) => call("patch", path, init) as never,
    put: (path, init = {}) => call("put", path, init) as never,
    postForm: (path, init) => call("post", path, init) as never,
    getFile: (path, init = {}) => call("get", path, { ...init, file: true }) as never,
    href: (path) => resolveUrl(options.base, path),
  };
}
