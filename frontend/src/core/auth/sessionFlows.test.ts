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
import { ApiError } from "../api/errors";
import { parseRole } from "./me";
import { Session } from "./session";
import { singleFlight } from "./singleFlight";

function setup(routes: Record<string, Reply | Reply[]>) {
  const fake = createFakeFetch(routes);
  const api = createAuthApi(
    createApiClient({ base: "/api", deviceId: () => "d", fetch: fake.fetch }),
  );
  return { fake, api, session: new Session(api, "Android — Chrome") };
}

const LOGIN = { phone: "677001122", secret: "482915", kind: "pin" } as const;

describe("Session — connexion et code", () => {
  it("connexion par code : envoie pin et le libellé de l'appareil", async () => {
    const { session, fake } = setup({
      [ROUTES.login]: json(200, tokenBody("t1", true)),
      [ROUTES.me]: json(200, meBody({ must_change_pin: true })),
    });
    await session.login(LOGIN);
    expect(fake.calls[0]?.body).toEqual({
      phone: "677001122",
      pin: "482915",
      device_label: "Android — Chrome",
    });
    expect(session.state.get()).toMatchObject({ me: { mustChangePin: true } });
  });

  it("connexion administrateur : envoie password", async () => {
    const { session, fake } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.me]: json(200, meBody({ is_platform_admin: true, shops: [] })),
    });
    await session.login({ phone: "677001122", secret: "mot-de-passe-long", kind: "password" });
    expect(fake.calls[0]?.body).toMatchObject({ password: "mot-de-passe-long" });
  });

  it("une réponse de jeton illisible est refusée", async () => {
    const { session } = setup({
      [ROUTES.login]: json(200, { ...tokenBody("t1"), expires_at: "jamais" }),
    });
    await expect(session.login(LOGIN)).rejects.toThrow("Réponse de session invalide");
  });

  it("PIN_CHANGE_REQUIRED sur un appel : le changement de code devient obligatoire", async () => {
    const { session, api } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.me]: [
        json(200, meBody()),
        apiError(403, "PIN_CHANGE_REQUIRED", "Choisissez un code"),
      ],
    });
    await session.login(LOGIN);
    await expect(session.authorized((t) => api.me(t))).rejects.toMatchObject({
      code: "PIN_CHANGE_REQUIRED",
    });
    expect(session.state.get()).toMatchObject({ status: "signedIn", me: { mustChangePin: true } });
  });

  it("code actuel faux (422 CURRENT_PIN_INVALID) : ni refresh ni déconnexion", async () => {
    const { session, fake } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.me]: json(200, meBody()),
      [ROUTES.changePin]: apiError(422, "CURRENT_PIN_INVALID", "Code actuel incorrect", {
        remaining_attempts: 3,
      }),
    });
    await session.login(LOGIN);
    const body = { current_pin: "111111", new_pin: "582914", new_pin_confirmation: "582914" };
    await expect(session.changePin(body)).rejects.toMatchObject({ code: "CURRENT_PIN_INVALID" });
    expect(fake.count(ROUTES.refresh)).toBe(0);
    expect(session.state.get().status).toBe("signedIn");
  });

  it("changement réussi : /me relu, le code provisoire n'est plus exigé", async () => {
    const { session } = setup({
      [ROUTES.login]: json(200, tokenBody("t1", true)),
      [ROUTES.me]: [json(200, meBody({ must_change_pin: true })), json(200, meBody())],
      [ROUTES.changePin]: new Response(null, { status: 204 }),
    });
    await session.login(LOGIN);
    await session.changePin({
      current_pin: "482915",
      new_pin: "582914",
      new_pin_confirmation: "582914",
    });
    expect(session.state.get()).toMatchObject({ me: { mustChangePin: false } });
  });

  it("compte désactivé au refresh : déconnecté avec le message du serveur", async () => {
    const { session } = setup({
      [ROUTES.refresh]: apiError(
        403,
        "ACCOUNT_DISABLED",
        "Compte désactivé, contactez le propriétaire",
      ),
    });
    await session.restore();
    expect(session.state.get()).toEqual({
      status: "signedOut",
      notice: "Compte désactivé, contactez le propriétaire",
    });
  });
});

describe("Session — déconnexion", () => {
  it("déconnexion volontaire, y compris si le serveur a déjà fermé la session (401)", async () => {
    for (const reply of [
      new Response(null, { status: 204 }),
      apiError(401, "UNAUTHENTICATED", "x"),
    ]) {
      const { session } = setup({
        [ROUTES.login]: json(200, tokenBody("t1")),
        [ROUTES.me]: json(200, meBody()),
        [ROUTES.logout]: reply,
      });
      await session.login(LOGIN);
      await session.logout();
      expect(session.state.get()).toEqual({ status: "signedOut", notice: null });
    }
  });

  it("déconnexion impossible (serveur en erreur) : l'erreur remonte, la session reste", async () => {
    const { session } = setup({
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.me]: json(200, meBody()),
      [ROUTES.logout]: apiError(500, "INTERNAL_ERROR", "Erreur interne du serveur"),
    });
    await session.login(LOGIN);
    await expect(session.logout()).rejects.toBeInstanceOf(ApiError);
    expect(session.state.get().status).toBe("signedIn");
  });
});

describe("singleFlight et rôles", () => {
  it("partage la promesse en cours puis relance une nouvelle exécution", async () => {
    let runs = 0;
    const once = singleFlight(() => Promise.resolve(++runs));
    expect(await Promise.all([once(), once(), once()])).toEqual([1, 1, 1]);
    expect(await once()).toBe(2);
  });

  it("libère le verrou après un échec", async () => {
    let runs = 0;
    const once = singleFlight(() => {
      runs++;
      return Promise.reject(new Error("refus"));
    });
    await expect(Promise.all([once(), once()])).rejects.toThrow("refus");
    await expect(once()).rejects.toThrow("refus");
    expect(runs).toBe(2);
  });

  it("parseRole n'accepte que les quatre rôles connus", () => {
    expect(parseRole("driver")).toBe("driver");
    expect(() => parseRole("admin")).toThrow("Rôle inconnu");
  });
});
