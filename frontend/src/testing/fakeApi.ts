/**
 * Faux serveur pour les tests : `fetch` programmable, route par route. Réservé aux tests
 * (exclu de la couverture) ; une route non prévue fait échouer le test (fail-fast).
 */
import type { MeResponse, TokenResponse } from "../core/api/types";

export interface Call {
  method: string;
  url: string;
  headers: Headers;
  body: unknown;
  /** Corps `multipart/form-data` (envoi de pièce jointe), sinon `undefined`. */
  form?: FormData;
  credentials: RequestCredentials | undefined;
}

export type Reply =
  Response | Error | DOMException | ((call: Call) => Response | Promise<Response>);

export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function apiError(
  status: number,
  code: string,
  message: string,
  details: Record<string, unknown> = {},
): Response {
  return json(status, { error: { code, message, details } });
}

export function tokenBody(
  token: string,
  mustChangePin = false,
  ttlMs = 15 * 60_000,
): TokenResponse {
  return {
    access_token: token,
    token_type: "bearer",
    expires_at: new Date(Date.now() + ttlMs).toISOString(),
    must_change_pin: mustChangePin,
  };
}

export const SHOP_A = "01890a5d-ac96-774b-bcce-b302099a8057";
export const SHOP_B = "01890a5d-ac96-774b-bcce-b302099a8058";

export function meBody(overrides: Partial<MeResponse> = {}): MeResponse {
  return {
    user_id: "01890a5d-ac96-774b-bcce-b302099a8000",
    name: "Awa Bello",
    phone: "+237677001122",
    is_platform_admin: false,
    must_change_pin: false,
    shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role: "seller" }],
    ...overrides,
  };
}

/** `routes["POST /api/v1/auth/login"] = [réponse 1, réponse 2…]` ; la dernière se répète. */
export function createFakeFetch(routes: Record<string, Reply | Reply[]>) {
  const calls: Call[] = [];
  const served = new Map<string, number>();
  const fakeFetch = async (input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const method = init.method ?? "GET";
    const text = typeof init.body === "string" ? init.body : undefined;
    const call: Call = {
      method,
      url,
      headers: new Headers(init.headers),
      body: text === undefined ? undefined : (JSON.parse(text) as unknown),
      ...(init.body instanceof FormData ? { form: init.body } : {}),
      credentials: init.credentials,
    };
    calls.push(call);
    const key = `${method} ${url}`;
    const entry = routes[key];
    if (entry === undefined) throw new Error(`Faux serveur : route non prévue « ${key} »`);
    const list = Array.isArray(entry) ? entry : [entry];
    const index = served.get(key) ?? 0;
    served.set(key, index + 1);
    const reply = list[Math.min(index, list.length - 1)];
    if (reply === undefined) throw new Error(`Faux serveur : aucune réponse pour « ${key} »`);
    if (reply instanceof Error || reply instanceof DOMException) throw reply;
    return typeof reply === "function" ? reply(call) : reply.clone();
  };
  const count = (key: string) => calls.filter((c) => `${c.method} ${c.url}` === key).length;
  const typedFetch: typeof fetch = fakeFetch;
  return { fetch: typedFetch, calls, count };
}

export const ROUTES = {
  login: "POST /api/v1/auth/login",
  refresh: "POST /api/v1/auth/refresh",
  logout: "POST /api/v1/auth/logout",
  changePin: "POST /api/v1/auth/change-pin",
  me: "GET /api/v1/me",
} as const;

export const NO_SESSION = () =>
  apiError(401, "UNAUTHENTICATED", "Session absente sur cet appareil");
