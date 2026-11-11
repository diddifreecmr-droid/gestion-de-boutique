import { describe, expect, it } from "vitest";
import {
  apiError,
  createFakeFetch,
  json,
  meBody,
  NO_SESSION,
  ROUTES,
  tokenBody,
  type Call,
  type Reply,
} from "../../testing/fakeApi";
import { createAuthApi } from "../api/auth";
import { createApiClient } from "../api/client";
import { NetworkError } from "../api/errors";
import { Session } from "./session";
import { SESSION_EXPIRED_NOTICE, SessionEndedError } from "./sessionState";

const PROBE = "GET /api/v1/me";

function setup(routes: Record<string, Reply | Reply[]>, now?: () => number) {
  const fake = createFakeFetch(routes);
  const client = createApiClient({ base: "/api", deviceId: () => "d", fetch: fake.fetch });
  const api = createAuthApi(client);
  const session = new Session(api, "Android — Chrome", now);
  return { fake, session, api };
}

const bearer = (call: Call | undefined) => call?.headers.get("Authorization");
/** /me : 401 avec l'ancien jeton, 200 avec le nouveau. */
const meAcceptsOnly = (token: string) => (call: Call) =>
  bearer(call) === `Bearer ${token}`
    ? json(200, meBody())
    : apiError(401, "UNAUTHENTICATED", "Jeton expiré");

describe("Session — restauration au chargement", () => {
  it("rafraîchit silencieusement puis lit /me", async () => {
    const { session, fake } = setup({
      [ROUTES.refresh]: json(200, tokenBody("t1")),
      [ROUTES.me]: json(200, meBody()),
    });
    await session.restore();
    expect(session.state.get()).toMatchObject({ status: "signedIn", me: { name: "Awa Bello" } });
    expect(bearer(fake.calls[1])).toBe("Bearer t1");
  });

  it("sans session sur l'appareil : déconnecté, sans message", async () => {
    const { session } = setup({ [ROUTES.refresh]: NO_SESSION() });
    await Promise.all([session.restore(), session.restore()]);
    expect(session.state.get()).toEqual({ status: "signedOut", notice: null });
  });

  it("session révoquée à distance : déconnecté avec le motif", async () => {
    const { session } = setup({
      [ROUTES.refresh]: apiError(401, "SESSION_REVOKED", "Session terminée sur cet appareil"),
    });
    await session.restore();
    expect(session.state.get()).toEqual({
      status: "signedOut",
      notice: "Session terminée sur cet appareil",
    });
  });

  it("serveur injoignable : état « échec » (session gardée), puis nouvel essai", async () => {
    const { session } = setup({
      [ROUTES.refresh]: [new TypeError("Failed to fetch"), json(200, tokenBody("t1"))],
      [ROUTES.me]: json(200, meBody()),
    });
    await session.restore();
    const state = session.state.get();
    expect(state.status).toBe("failed");
    expect(state.status === "failed" && state.error).toBeInstanceOf(NetworkError);
    await session.retryRestore();
    expect(session.state.get().status).toBe("signedIn");
  });

  it("un rôle inconnu renvoyé par /me est une erreur visible (fail-fast)", async () => {
    const { session } = setup({
      [ROUTES.refresh]: json(200, tokenBody("t1")),
      [ROUTES.me]: json(200, meBody({ shops: [{ shop_id: "s", shop_name: "B", role: "pilote" }] })),
    });
    await session.restore();
    const state = session.state.get();
    expect(state.status === "failed" && state.error.message).toContain("Rôle inconnu");
  });
});

describe("Session — rafraîchissement single-flight", () => {
  it("plusieurs 401 simultanés → un seul refresh, puis chaque appel est rejoué", async () => {
    const { session, fake, api } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.refresh]: json(200, tokenBody("t2")),
      [ROUTES.me]: [json(200, meBody()), meAcceptsOnly("t2")],
    });
    await session.login({ phone: "677001122", secret: "482915", kind: "pin" });
    const results = await Promise.all(
      [1, 2, 3].map(() => session.authorized((token) => api.me(token))),
    );
    expect(results).toHaveLength(3);
    expect(fake.count(ROUTES.refresh)).toBe(1);
    const replays = fake.calls.filter((c) => c.url.endsWith("/me") && bearer(c) === "Bearer t2");
    expect(replays).toHaveLength(3);
  });

  it("rafraîchit avant l'expiration (moins de 30 s restantes) sans attendre un 401", async () => {
    const { session, fake, api } = setup({
      [ROUTES.login]: json(200, tokenBody("t1", false, 10_000)),
      [ROUTES.refresh]: json(200, tokenBody("t2")),
      [ROUTES.me]: meAcceptsOnly("t2"),
    });
    await session.login({ phone: "677001122", secret: "482915", kind: "pin" });
    await session.authorized((token) => api.me(token));
    expect(fake.count(ROUTES.refresh)).toBe(1);
    expect(fake.calls.filter((c) => bearer(c) === "Bearer t1")).toHaveLength(0);
  });

  it("refresh refusé pendant la session → déconnexion propre avec message", async () => {
    const { session, api } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.refresh]: NO_SESSION(),
      [ROUTES.me]: [json(200, meBody()), apiError(401, "UNAUTHENTICATED", "Jeton expiré")],
    });
    await session.login({ phone: "677001122", secret: "482915", kind: "pin" });
    await expect(session.authorized((t) => api.me(t))).rejects.toBeInstanceOf(SessionEndedError);
    expect(session.state.get()).toEqual({ status: "signedOut", notice: SESSION_EXPIRED_NOTICE });
    await expect(session.authorized((t) => api.me(t))).rejects.toBeInstanceOf(SessionEndedError);
  });

  it("SESSION_REVOKED sur un appel → déconnexion immédiate, sans refresh", async () => {
    const revoked = apiError(401, "SESSION_REVOKED", "Session terminée sur cet appareil");
    const { session, fake, api } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.me]: [json(200, meBody()), revoked],
    });
    await session.login({ phone: "677001122", secret: "482915", kind: "pin" });
    await expect(session.authorized((t) => api.me(t))).rejects.toBeInstanceOf(SessionEndedError);
    expect(session.state.get()).toEqual({
      status: "signedOut",
      notice: "Session terminée sur cet appareil",
    });
    expect(fake.count(ROUTES.refresh)).toBe(0);
    expect(fake.count(PROBE)).toBe(2);
  });
});
