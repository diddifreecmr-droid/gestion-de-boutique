import { act, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { updateStoreForTests } from "../core/pwa/appUpdate";
import { reloadLatestVersion } from "../core/pwa/reload";
import { json, meBody, ROUTES, SHOP_A, tokenBody } from "../testing/fakeApi";
import { axeViolations } from "../testing/axe";
import { renderApp } from "../testing/renderApp";

vi.mock("../core/pwa/reload", () => ({ reloadLatestVersion: vi.fn(() => Promise.resolve()) }));

function openAs(role: string, path = `/s/${SHOP_A}`) {
  return renderApp(path, {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(
      200,
      meBody({ shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }] }),
    ),
    [ROUTES.logout]: new Response(null, { status: 204 }),
    [`GET /api/v1/shops/${SHOP_A}/alerts?unread_only=true`]: json(200, {
      items: [],
      next_cursor: null,
      unread_count: 0,
    }),
  });
}

const nav = () => within(screen.getByRole("navigation", { name: "Navigation principale" }));
const topBar = () => within(screen.getByRole("banner"));

afterEach(() => {
  updateStoreForTests.set(null);
});

describe("coquille — menus par rôle (CDC § 17.4)", () => {
  it.each([
    // Modules à venir (transfers, transport) : leurs entrées n'apparaissent jamais (13/11/2026).
    ["owner", ["Accueil", "Ventes", "Stock", "Plus"]],
    ["accountant", ["Accueil", "Achats", "Stock", "Dépenses"]],
    ["driver", ["Mon voyage"]],
  ])("%s : barre du bas et titre de l'accueil", async (role, labels) => {
    openAs(role);
    const [home = ""] = labels;
    expect(await screen.findByRole("heading", { level: 1, name: home })).toBeInTheDocument();
    expect(
      nav()
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(labels);
  });

  it("l'adresse d'un écran à venir donne « Page introuvable », jamais « arrive bientôt »", async () => {
    openAs("accountant", `/s/${SHOP_A}/deplacements`);
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
    expect(screen.queryByText(/arrive bientôt|Disponible au Lot/)).toBeNull();
  });

  it("« Plus » du propriétaire sans « Mon compte » ni « Paie » ; « Compte » (barre du haut) : version et « Recharger »", async () => {
    const { user } = openAs("owner");
    await user.click(await screen.findByRole("link", { name: "Plus" }));
    const main = within(screen.getByRole("main"));
    const tiles = main.getAllByRole("button").map((b) => b.textContent);
    expect(tiles).toEqual(expect.arrayContaining(["Créances", "Journal", "Réglages"]));
    expect(tiles).not.toContain("Mon compte");
    expect(tiles).not.toContain("Paie");
    await user.click(main.getByRole("button", { name: "Réglages" }));
    expect(await screen.findByRole("heading", { name: "Réglages" })).toBeVisible();
    expect(nav().getByRole("link", { name: "Plus" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("list", { name: "Mon compte" })).toBeNull();
    await user.click(topBar().getByRole("button", { name: "Mon compte" }));
    expect(await screen.findByText("0.0.0-test")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Recharger la dernière version" }));
    expect(reloadLatestVersion).toHaveBeenCalledOnce();
  });

  it("la cloche ouvre les alertes de l'utilisateur", async () => {
    const { user } = openAs("seller");
    await user.click(await screen.findByRole("button", { name: "Alertes, aucune nouvelle" }));
    expect(await screen.findByRole("heading", { name: "Alertes" })).toBeVisible();
    expect(await screen.findByText("Aucune alerte à traiter.")).toBeVisible();
  });
});

describe("coquille — compte et bannières", () => {
  it.each(["owner", "seller", "accountant", "driver"])(
    "%s : « Compte » dans la barre du haut, à droite de la cloche, ouvre « Mon compte »",
    async (role) => {
      const { user, router, container } = openAs(role);
      await screen.findByText("Motos Garoua");
      const buttons = topBar().getAllByRole("button");
      expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([
        "Alertes, aucune nouvelle",
        "Mon compte",
      ]);
      expect(await axeViolations(container)).toEqual([]);
      await user.click(topBar().getByRole("button", { name: "Mon compte" }));
      expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/compte`);
      expect(screen.getByRole("heading", { name: "Mon compte" })).toBeVisible();
      expect(screen.getByRole("button", { name: "Recharger la dernière version" })).toBeVisible();
      expect(await axeViolations(container)).toEqual([]);
    },
  );

  it("« Mon compte » (barre du haut) : déconnexion après confirmation", async () => {
    const { user, router } = openAs("seller");
    await screen.findByText("Motos Garoua");
    expect(
      within(screen.getByRole("main")).queryByRole("button", { name: "Mon compte" }),
    ).toBeNull();
    await user.click(topBar().getByRole("button", { name: "Mon compte" }));
    await user.click(screen.getByRole("button", { name: "Se déconnecter" }));
    const dialog = screen.getByRole("dialog", { name: "Se déconnecter ?" });
    await user.click(within(dialog).getByRole("button", { name: "Se déconnecter" }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/connexion");
    });
  });

  it("« Recharger la dernière version » en échec : erreur affichée, bouton de nouveau actif", async () => {
    vi.mocked(reloadLatestVersion).mockRejectedValueOnce(new Error("désinscription refusée"));
    const { user } = openAs("seller", `/s/${SHOP_A}/compte`);
    await user.click(await screen.findByRole("button", { name: "Recharger la dernière version" }));
    expect(
      await screen.findByText("Rechargement impossible : désinscription refusée"),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Recharger la dernière version" })).toBeEnabled();
  });

  it("« Mon compte » : changer mon code ouvre l'écran dédié", async () => {
    const { user, router } = openAs("driver", `/s/${SHOP_A}/compte`);
    await user.click(await screen.findByRole("button", { name: "Changer mon code" }));
    expect(router.state.location.pathname).toBe("/changer-code");
  });

  it("hors ligne : « Connexion nécessaire » sous la barre du haut", async () => {
    openAs("seller");
    await screen.findByText("Motos Garoua");
    act(() => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByText("Connexion nécessaire")).toBeVisible();
    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.queryByText("Connexion nécessaire")).not.toBeInTheDocument();
  });

  it("nouvelle version en attente : bannière « Mettre à jour »", async () => {
    openAs("seller");
    await screen.findByText("Motos Garoua");
    act(() => {
      updateStoreForTests.set({} as ServiceWorker);
    });
    expect(screen.getByText("Nouvelle version disponible")).toBeVisible();
    expect(screen.getByRole("button", { name: "Mettre à jour" })).toBeVisible();
  });
});
