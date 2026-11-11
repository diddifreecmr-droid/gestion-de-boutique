import { describe, expect, expectTypeOf, it, vi } from "vitest";
import { apiError, createFakeFetch, json, meBody, ROUTES, tokenBody } from "../../testing/fakeApi";
import { createAuthApi } from "./auth";
import { createApiClient, resolveUrl, type ResponseOf } from "./client";
import { ApiError, NetworkError, parseErrorEnvelope } from "./errors";
import type { MeResponse, TokenResponse } from "./types";

const DEVICE = "01890a5d-ac96-774b-bcce-b302099a8001";

function setup(routes: Parameters<typeof createFakeFetch>[0]) {
  const fake = createFakeFetch(routes);
  const hooks = { onResponse: vi.fn(), onNetworkFailure: vi.fn() };
  const client = createApiClient({
    base: "/api",
    deviceId: () => DEVICE,
    fetch: fake.fetch,
    ...hooks,
  });
  return { fake, hooks, api: createAuthApi(client) };
}

describe("client API — en-têtes", () => {
  it("envoie X-Device-Id, le corps JSON et le cookie (credentials include), sans Authorization", async () => {
    const { fake, api } = setup({ [ROUTES.login]: json(200, tokenBody("t1")) });
    const body = { phone: "677001122", pin: "482915", device_label: "Android — Chrome" };
    await expect(api.login(body)).resolves.toMatchObject({ access_token: "t1" });
    const [call] = fake.calls;
    expect(call?.url).toBe("/api/v1/auth/login");
    expect(call?.headers.get("X-Device-Id")).toBe(DEVICE);
    expect(call?.headers.get("Content-Type")).toBe("application/json");
    expect(call?.headers.get("Authorization")).toBeNull();
    expect(call?.credentials).toBe("include");
    expect(call?.body).toEqual(body);
  });

  it("ajoute Authorization: Bearer quand un jeton est fourni", async () => {
    const { fake, api, hooks } = setup({ [ROUTES.me]: json(200, meBody()) });
    await expect(api.me("jeton")).resolves.toMatchObject({ name: "Awa Bello" });
    expect(fake.calls[0]?.headers.get("Authorization")).toBe("Bearer jeton");
    expect(fake.calls[0]?.headers.get("Content-Type")).toBeNull();
    expect(hooks.onResponse).toHaveBeenCalledOnce();
  });

  it("ajoute les en-têtes propres à l'appel, refuse ceux du client", async () => {
    const fake = createFakeFetch({ [ROUTES.me]: json(200, meBody()) });
    const client = createApiClient({ base: "/api", deviceId: () => DEVICE, fetch: fake.fetch });
    const at = "2026-11-11T10:05:00.000+01:00";
    await client.get("/api/v1/me", { headers: { "X-Captured-At": at } });
    expect(fake.calls[0]?.headers.get("X-Captured-At")).toBe(at);
    expect(fake.calls[0]?.headers.get("X-Device-Id")).toBe(DEVICE);
    await expect(client.get("/api/v1/me", { headers: { "x-device-id": "autre" } })).rejects.toThrow(
      "réservé au client API",
    );
    expect(fake.calls).toHaveLength(1);
  });

  it("renvoie undefined pour une réponse 204", async () => {
    const { api } = setup({ [ROUTES.logout]: new Response(null, { status: 204 }) });
    await expect(api.logout()).resolves.toBeUndefined();
  });
});

describe("client API — erreurs", () => {
  it("lit l'enveloppe {error: {code, message, details}} en ApiError typée", async () => {
    const until = "2026-11-11T13:32:00+00:00";
    const { api } = setup({
      [ROUTES.login]: apiError(423, "ACCOUNT_LOCKED", "Compte bloqué", { until }),
    });
    const error = await api
      .login({ phone: "1", pin: "1", device_label: "x" })
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 423,
      code: "ACCOUNT_LOCKED",
      message: "Compte bloqué",
      details: { until },
    });
  });

  it("une réponse d'erreur sans enveloppe (proxy) donne HTTP_<statut>", async () => {
    const { api } = setup({
      [ROUTES.refresh]: new Response("<html>Bad gateway</html>", { status: 502 }),
    });
    await expect(api.refresh()).rejects.toMatchObject({ status: 502, code: "HTTP_502" });
    expect(parseErrorEnvelope(500, { error: { code: 1 } }).code).toBe("HTTP_500");
    const noDetails = parseErrorEnvelope(400, { error: { code: "X", message: "m", details: [] } });
    expect(noDetails.details).toEqual({});
  });

  it("un succès illisible n'est jamais pris pour une réponse valide", async () => {
    const { api } = setup({ [ROUTES.me]: new Response("pas du JSON", { status: 200 }) });
    await expect(api.me("t")).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
  });

  it("une coupure réseau lève NetworkError et prévient la connectivité", async () => {
    const { api, hooks } = setup({ [ROUTES.me]: new TypeError("Failed to fetch") });
    const error = await api.me("t").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(NetworkError);
    expect((error as NetworkError).cause).toBeInstanceOf(TypeError);
    expect(hooks.onNetworkFailure).toHaveBeenCalledWith(error);
    expect(hooks.onResponse).not.toHaveBeenCalled();
  });

  it("une annulation (AbortError) est relancée telle quelle", async () => {
    const abort = new DOMException("annulé", "AbortError");
    const { api, hooks } = setup({ [ROUTES.me]: abort });
    await expect(api.me("t")).rejects.toBe(abort);
    expect(hooks.onNetworkFailure).not.toHaveBeenCalled();
  });
});

describe("client API — adresses et types", () => {
  it("remplace le préfixe /api du contrat par VITE_API_BASE", () => {
    expect(resolveUrl("/api", "/api/v1/me")).toBe("/api/v1/me");
    expect(resolveUrl("https://boutique.example/api", "/api/v1/me")).toBe(
      "https://boutique.example/api/v1/me",
    );
    expect(() => resolveUrl("/api/", "/api/v1/me")).toThrow("ne doit pas finir par");
    expect(() => resolveUrl("/api", "/v1/me")).toThrow("Chemin hors contrat");
  });

  it("type les réponses depuis schema.gen.ts", () => {
    expectTypeOf<ResponseOf<"/api/v1/me", "get">>().toEqualTypeOf<MeResponse>();
    expectTypeOf<ResponseOf<"/api/v1/auth/refresh", "post">>().toEqualTypeOf<TokenResponse>();
    expectTypeOf<ResponseOf<"/api/v1/auth/logout", "post">>().toEqualTypeOf<undefined>();
  });
});
