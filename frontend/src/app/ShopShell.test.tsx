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
  });
}

const nav = () => within(screen.getByRole("navigation", { name: "Navigation principale" }));
const topBar = () => within(screen.getByRole("banner"));

afterEach(() => {
  updateStoreForTests.set(null);
});

describe("coquille — menus par rôle (CDC § 17.4)", () => {
  it.each([
    ["owner", ["Accueil", "Ventes", "Stock", "Camions", "Plus"], "Propriétaire"],
    ["accountant", ["Accueil", "Achats", "Stock", "Déplacements", "Dépenses"], "Comptable"],
    ["driver", ["Mon voyage", "Mes dépenses", "Mes voyages"], "Chauffeur"],
  ])("%s : barre du bas et accueil provisoire", async (role, labels, roleLabel) => {
    openAs(role);
    expect(await screen.findByText(new RegExp(`Bonjour Awa Bello — ${roleLabel}`))).toBeVisible();
    expect(
      nav()
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(labels);
  });

  it("une entrée ouvre sa page provisoire « à venir » et devient active", async () => {
    const { user, router } = openAs("seller");
    await user.click(await screen.findByRole("link", { name: "Mes ventes" }));
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/mes-ventes`);
    expect(screen.getByRole("heading", { name: "Mes ventes" })).toBeVisible();
    expect(screen.getByText("Cet écran arrive bientôt.")).toBeVisible();
    expect(nav().getByRole("link", { name: "Mes ventes" })).toHaveAttribute("aria-current", "page");
  });

  it("« Plus » du propriétaire, puis Réglages : version et « Recharger la dernière version »", async () => {
    const { user } = openAs("owner");
    await user.click(await screen.findByRole("link", { name: "Plus" }));
    const tiles = screen.getAllByRole("button").map((b) => b.textContent);
    expect(tiles).toEqual(
      expect.arrayContaining(["Créances", "Paie", "Journal", "Réglages", "Mon compte"]),
    );
    await user.click(screen.getByRole("button", { name: "Réglages" }));
    expect(screen.getByRole("heading", { name: "Réglages" })).toBeVisible();
    expect(screen.getByText("0.0.0-test")).toBeVisible();
    expect(nav().getByRole("link", { name: "Plus" })).toHaveAttribute("aria-current", "page");
    await user.click(screen.getByRole("button", { name: "Recharger la dernière version" }));
    expect(reloadLatestVersion).toHaveBeenCalledOnce();
  });

  it("la cloche ouvre les alertes (provisoire)", async () => {
    const { user } = openAs("seller");
    await user.click(await screen.findByRole("button", { name: "Alertes, aucune nouvelle" }));
    expect(screen.getByRole("heading", { name: "Alertes" })).toBeVisible();
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

  it("« Mon compte » depuis l'accueil : déconnexion après confirmation", async () => {
    const { user, router } = openAs("seller");
    await screen.findByText(/Bonjour Awa Bello/);
    await user.click(within(screen.getByRole("main")).getByRole("button", { name: "Mon compte" }));
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
