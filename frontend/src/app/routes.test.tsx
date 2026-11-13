import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  json,
  meBody,
  NO_SESSION,
  ROUTES,
  SHOP_A,
  SHOP_B,
  tokenBody,
  type Reply,
} from "../testing/fakeApi";
import { renderApp } from "../testing/renderApp";
import { UI_SHOWCASE_PATH } from "./routes";

/** Session restaurée au chargement (refresh puis /me). */
function signedIn(me = meBody()): Record<string, Reply | Reply[]> {
  return { [ROUTES.refresh]: json(200, tokenBody("t1")), [ROUTES.me]: json(200, me) };
}

const navLabels = () =>
  within(screen.getByRole("navigation", { name: "Navigation principale" }))
    .getAllByRole("link")
    .map((link) => link.textContent);

describe("garde de route", () => {
  it("non connecté → écran de connexion, l'adresse demandée est gardée", async () => {
    const { router } = renderApp(`/s/${SHOP_A}/stock`, { [ROUTES.refresh]: NO_SESSION() });
    expect(await screen.findByRole("heading", { name: "Connexion" })).toBeVisible();
    expect(router.state.location.pathname).toBe("/connexion");
    expect(router.state.location.state).toEqual({ from: `/s/${SHOP_A}/stock` });
  });

  it("affiche le chargement pendant la restauration silencieuse", () => {
    renderApp("/", { [ROUTES.refresh]: () => new Promise<Response>(() => undefined) });
    expect(screen.getByText("Ouverture de votre session…")).toBeInTheDocument();
  });

  it("code provisoire → changement de code obligatoire, quelle que soit l'adresse", async () => {
    const { router } = renderApp(`/s/${SHOP_A}`, signedIn(meBody({ must_change_pin: true })));
    expect(await screen.findByRole("heading", { name: "Changer mon code" })).toBeVisible();
    expect(router.state.location.pathname).toBe("/changer-code");
  });

  it("connecté sur /connexion → renvoyé à l'accueil de sa boutique", async () => {
    const { router } = renderApp("/connexion", signedIn());
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/s/${SHOP_A}`);
    });
  });

  it("restauration impossible (réseau) → motif affiché et « Réessayer »", async () => {
    renderApp("/", { [ROUTES.refresh]: new TypeError("Failed to fetch") });
    expect(await screen.findByRole("heading", { name: "Session non ouverte" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeVisible();
    expect(screen.getByText("Connexion nécessaire")).toBeVisible();
  });
});

describe("boutique active (UC-SOC-03)", () => {
  it("une seule boutique : ouverte directement, barre du bas du vendeur", async () => {
    const { router } = renderApp("/", signedIn());
    expect(await screen.findByText("Motos Garoua")).toBeVisible();
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}`);
    expect(navLabels()).toEqual(["Accueil", "Nouvelle vente", "Mes ventes", "Créances", "Stock"]);
    expect(screen.getByRole("link", { name: "Accueil" })).toHaveAttribute("aria-current", "page");
  });

  it("plusieurs boutiques : liste, puis le nom en haut ramène à la liste", async () => {
    const shops = [
      { shop_id: SHOP_A, shop_name: "Motos Garoua", role: "owner" },
      { shop_id: SHOP_B, shop_name: "Motos Ngaoundéré", role: "accountant" },
    ];
    const { router, user } = renderApp("/", signedIn(meBody({ shops })));
    expect(await screen.findByRole("heading", { name: "Choisir une boutique" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Motos Ngaoundéré/ }));
    expect(router.state.location.pathname).toBe(`/s/${SHOP_B}`);
    // Menu servi par le profil de cette boutique pour ce rôle (Déplacements : module à venir).
    expect(await screen.findByRole("link", { name: "Achats" })).toBeVisible();
    expect(navLabels()).toEqual(["Accueil", "Achats", "Stock", "Dépenses"]);
    await user.click(screen.getByRole("button", { name: "Motos Ngaoundéré" }));
    expect(router.state.location.pathname).toBe("/boutiques");
  });

  it("boutique étrangère ou section hors des droits du rôle → page introuvable", async () => {
    renderApp(`/s/${SHOP_B}`, signedIn());
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });

  it("section interdite au vendeur (Paie) → page introuvable", async () => {
    renderApp(`/s/${SHOP_A}/paie`, signedIn());
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });

  it("administrateur plateforme → console", async () => {
    const { router } = renderApp("/", {
      ...signedIn(meBody({ is_platform_admin: true, shops: [] })),
      "GET /api/v1/platform/shops": json(200, []),
    });
    expect(await screen.findByText("Console plateforme")).toBeVisible();
    expect(await screen.findByText("Aucune boutique pour l'instant.")).toBeVisible();
    expect(router.state.location.pathname).toBe("/plateforme");
  });

  it("aucune boutique rattachée → message clair", async () => {
    renderApp("/", signedIn(meBody({ shops: [] })));
    expect(await screen.findByRole("heading", { name: "Aucune boutique" })).toBeVisible();
  });
});

describe("routes", () => {
  it("affiche une page introuvable pour une adresse inconnue", async () => {
    renderApp("/nulle-part", { [ROUTES.refresh]: NO_SESSION() });
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });

  it("sert la vitrine /_ui en développement", async () => {
    expect(import.meta.env.DEV).toBe(true);
    renderApp(UI_SHOWCASE_PATH, { [ROUTES.refresh]: NO_SESSION() });
    expect(await screen.findByRole("heading", { name: "Vitrine des composants" })).toBeVisible();
  });
});
