import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  apiError,
  json,
  meBody,
  NO_SESSION,
  ROUTES,
  SHOP_A,
  tokenBody,
  type Reply,
} from "../../testing/fakeApi";
import { HOME, homeBody } from "../../testing/dashboard";
import { renderApp } from "../../testing/renderApp";
import { formatTime } from "../../shared/format";

function openLogin(login: Reply | Reply[], extra: Record<string, Reply | Reply[]> = {}) {
  return renderApp("/connexion", {
    [ROUTES.refresh]: NO_SESSION(),
    [ROUTES.login]: login,
    [ROUTES.me]: json(200, meBody()),
    // Accueil du vendeur, ouvert après la connexion.
    [HOME]: json(200, homeBody("seller")),
    ...extra,
  });
}

async function fill(user: ReturnType<typeof openLogin>["user"], phone: string, pin: string) {
  const phoneField = await screen.findByLabelText("Numéro de téléphone");
  if (phone !== "") await user.type(phoneField, phone);
  if (pin !== "") await user.type(screen.getByLabelText(/Code secret/), pin);
  await user.click(screen.getByRole("button", { name: "Se connecter" }));
}

describe("écran de connexion (UC-SOC-02)", () => {
  it("téléphone + code à 6 chiffres, clavier numérique ; aucune violation axe", async () => {
    const { container } = openLogin(json(200, tokenBody("t1")));
    const phone = await screen.findByLabelText("Numéro de téléphone");
    const pin = screen.getByLabelText(/Code secret/);
    expect(phone).toHaveAttribute("type", "tel");
    expect(pin).toHaveAttribute("inputmode", "numeric");
    expect(pin).toHaveAttribute("maxlength", "6");
    expect(pin).toHaveAttribute("type", "password");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("contrôle la saisie avant l'envoi", async () => {
    const { user, fake } = openLogin(json(200, tokenBody("t1")));
    await fill(user, "", "12");
    expect(screen.getByText("Le numéro est vide")).toBeVisible();
    expect(screen.getByText("Le code doit avoir 6 chiffres")).toBeVisible();
    expect(fake.count(ROUTES.login)).toBe(0);
  });

  it("connexion réussie → accueil de la boutique", async () => {
    const { user, router, fake } = openLogin(json(200, tokenBody("t1")));
    await fill(user, "677 00 11 22", "482915");
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/s/${SHOP_A}`);
    });
    expect(fake.calls.find((c) => c.url.endsWith("/login"))?.body).toMatchObject({
      phone: "677 00 11 22",
      pin: "482915",
    });
  });

  it("code faux → message générique sur le champ ; saisie gardée", async () => {
    const { user } = openLogin(apiError(401, "UNAUTHENTICATED", "Numéro ou code incorrect"));
    await fill(user, "677001122", "000111");
    expect(await screen.findByText("Numéro ou code incorrect")).toBeVisible();
    expect(screen.getByLabelText("Numéro de téléphone")).toHaveValue("677001122");
  });

  it("compte bloqué → heure de fin « 14 h 32 » (Douala)", async () => {
    const until = "2026-11-11T13:32:00+00:00";
    const { user, container } = openLogin(
      apiError(423, "ACCOUNT_LOCKED", "Compte bloqué", { until }),
    );
    await fill(user, "677001122", "000111");
    // textContent brut : les espaces insécables de « 14 h 32 » sont vérifiées telles quelles.
    expect((await screen.findByText(/^Compte bloqué jusqu'à/)).textContent).toContain(
      `Compte bloqué jusqu'à ${formatTime("2026-11-11T13:32:00Z")}`,
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("compte désactivé, numéro invalide, erreur imprévue : messages clairs", async () => {
    const { user } = openLogin([
      apiError(403, "ACCOUNT_DISABLED", "Compte désactivé, contactez le propriétaire"),
      apiError(400, "VALIDATION_ERROR", "Numéro invalide", { field: "phone" }),
      apiError(500, "INTERNAL_ERROR", "Erreur interne du serveur"),
    ]);
    await fill(user, "677001122", "482915");
    expect(await screen.findByText("Compte désactivé, contactez le propriétaire")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByText("Numéro de téléphone invalide")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(
      await screen.findByText("Erreur interne du serveur (code INTERNAL_ERROR)"),
    ).toBeVisible();
  });

  it("hors connexion → « Connexion nécessaire », formulaire gardé, renvoi en un appui", async () => {
    const { user, router } = openLogin([
      new TypeError("Failed to fetch"),
      json(200, tokenBody("t1")),
    ]);
    await fill(user, "677001122", "482915");
    expect(await screen.findByText("Connexion nécessaire")).toBeVisible();
    expect(screen.getByLabelText(/Code secret/)).toHaveValue("482915");
    await user.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/s/${SHOP_A}`);
    });
    // L'écran de connexion (et son message) a laissé place à la boutique ; l'accueil peut, lui,
    // dire « Connexion nécessaire » pour ses propres lectures, non simulées ici.
    expect(screen.queryByRole("button", { name: "Se connecter" })).not.toBeInTheDocument();
  });

  it("motif de fin de session affiché (session révoquée à distance)", async () => {
    renderApp("/connexion", {
      [ROUTES.refresh]: apiError(401, "SESSION_REVOKED", "Session terminée sur cet appareil"),
    });
    expect(await screen.findByText("Session terminée sur cet appareil")).toBeVisible();
  });
});

describe("connexion administrateur plateforme", () => {
  it("mot de passe de 10 caractères au moins, envoyé comme password", async () => {
    const { user, fake, router, container } = renderApp("/connexion/admin", {
      [ROUTES.refresh]: NO_SESSION(),
      [ROUTES.login]: json(200, tokenBody("t1")),
      [ROUTES.me]: json(200, meBody({ is_platform_admin: true, shops: [] })),
      "GET /api/v1/platform/shops": json(200, []),
    });
    await user.type(await screen.findByLabelText("Numéro de téléphone"), "699000000");
    await user.type(screen.getByLabelText("Mot de passe"), "court");
    await user.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(screen.getByText("Le mot de passe doit avoir au moins 10 caractères")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.type(screen.getByLabelText("Mot de passe"), "-assez-long");
    await user.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/plateforme");
    });
    expect(fake.calls.find((c) => c.url.endsWith("/login"))?.body).toMatchObject({
      password: "court-assez-long",
    });
  });
});
