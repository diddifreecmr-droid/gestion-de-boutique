/**
 * Robustesse du rafraîchissement (audit du 2026-11-13, specs § 8.1) : un seul refresh pour
 * tous les appelants, y compris au démarrage ; un 401 qui ne vient pas de notre API (proxy,
 * portail captif) ou une coupure réseau ne déconnectent jamais.
 */
import { describe, expect, it } from "vitest";
import {
  apiError,
  createFakeFetch,
  json,
  meBody,
  ROUTES,
  tokenBody,
  type Reply,
} from "../../testing/fakeApi";
import { createAuthApi } from "../api/auth";
import { createApiClient } from "../api/client";
import { ApiError, NetworkError } from "../api/errors";
import { Session } from "./session";
import { endsSession, isServerVerdict } from "./sessionState";

function setup(routes: Record<string, Reply | Reply[]>) {
  const fake = createFakeFetch(routes);
  const client = createApiClient({ base: "/api", deviceId: () => "d", fetch: fake.fetch });
  const api = createAuthApi(client);
  return { fake, api, session: new Session(api, "Android — Chrome") };
}

/** 401 d'un intermédiaire : page HTML, sans l'enveloppe `{"error": …}` de l'API. */
const proxy401 = () =>
  new Response("<html>Authentification du réseau requise</html>", {
    status: 401,
    headers: { "Content-Type": "text/html" },
  });

const LOGIN = { phone: "677001122", secret: "482915", kind: "pin" } as const;

describe("Session — single-flight au démarrage", () => {
  it("restauration et appels des écrans en même temps → un seul refresh", async () => {
    const { session, fake, api } = setup({
      [ROUTES.refresh]: json(200, tokenBody("t1")),
      [ROUTES.me]: json(200, meBody()),
    });
    await Promise.all([
      session.restore(),
      session.restore(),
      session.authorized((token) => api.me(token)),
      session.authorized((token) => api.me(token)),
    ]);
    expect(fake.count(ROUTES.refresh)).toBe(1);
    expect(session.state.get().status).toBe("signedIn");
  });
});

describe("Session — 401 transitoire du réseau", () => {
  it("401 sans enveloppe pendant la restauration → « échec » avec Réessayer, pas déconnecté", async () => {
    const { session } = setup({
      [ROUTES.refresh]: [proxy401(), json(200, tokenBody("t1"))],
      [ROUTES.me]: json(200, meBody()),
    });
    await session.restore();
    expect(session.state.get().status).toBe("failed");
    await session.retryRestore();
    expect(session.state.get().status).toBe("signedIn");
  });

  it("401 sans enveloppe sur un appel → erreur remontée, ni refresh ni déconnexion", async () => {
    const { session, fake, api } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.me]: [json(200, meBody()), proxy401(), json(200, meBody())],
    });
    await session.login(LOGIN);
    await expect(session.authorized((t) => api.me(t))).rejects.toMatchObject({
      status: 401,
      code: "HTTP_401",
    });
    expect(fake.count(ROUTES.refresh)).toBe(0);
    expect(session.state.get().status).toBe("signedIn");
    await expect(session.authorized((t) => api.me(t))).resolves.toBeDefined();
  });

  it("refresh coupé (réseau) ou 401 d'un proxy pendant la session → toujours connecté", async () => {
    let meCalls = 0;
    const { session, fake, api } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.refresh]: [new TypeError("Failed to fetch"), proxy401(), json(200, tokenBody("t2"))],
      // /me : accepté à la connexion, puis seulement avec le jeton rafraîchi t2.
      [ROUTES.me]: (call) => {
        meCalls += 1;
        return meCalls === 1 || call.headers.get("Authorization") === "Bearer t2"
          ? json(200, meBody())
          : apiError(401, "UNAUTHENTICATED", "Jeton expiré");
      },
    });
    await session.login(LOGIN);
    await expect(session.authorized((t) => api.me(t))).rejects.toBeInstanceOf(NetworkError);
    expect(session.state.get().status).toBe("signedIn");
    await expect(session.authorized((t) => api.me(t))).rejects.toMatchObject({ code: "HTTP_401" });
    expect(session.state.get().status).toBe("signedIn");
    await expect(session.authorized((t) => api.me(t))).resolves.toBeDefined();
    expect(fake.count(ROUTES.refresh)).toBe(3);
  });
});

describe("endsSession", () => {
  it("seuls les refus de notre API terminent la session", () => {
    expect(endsSession(new ApiError(401, "UNAUTHENTICATED", "x"))).toBe(true);
    expect(endsSession(new ApiError(401, "SESSION_REVOKED", "x"))).toBe(true);
    expect(endsSession(new ApiError(403, "ACCOUNT_DISABLED", "x"))).toBe(true);
    expect(endsSession(new ApiError(401, "HTTP_401", "x"))).toBe(false);
    expect(endsSession(new NetworkError("coupure"))).toBe(false);
    expect(isServerVerdict(new ApiError(403, "HTTP_403", "x"))).toBe(false);
  });
});
