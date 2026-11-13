/**
 * T37 — la coquille suit le profil **servi** de la boutique : une boutique Prêt-à-porter ou
 * Textile n'affiche ni le vocabulaire ni les menus Motos (« Employé », pas de Chauffeur).
 */
import { configure, screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../testing/axe";
import { json, SHOP_A } from "../testing/fakeApi";
import { memberSession, preloadLot1Screens, SHOP_PATH } from "../testing/lot1Screens";
import { PROFILE_ROUTE } from "../testing/modules";
import type { ServedProfileCode } from "../testing/profileMenus";
import { renderApp } from "../testing/renderApp";
import { servedProfile } from "../testing/servedProfile";
import { preloadSettings, settingsRoutes, viewPath } from "../testing/shopSettingsApi";
import { stockRoutes } from "../testing/stock";

configure({ asyncUtilTimeout: 5000 });
beforeAll(async () => {
  await Promise.all([
    preloadLot1Screens(),
    preloadSettings(),
    import("../features/stock/StockRoute"),
  ]);
});
beforeEach(() => {
  window.localStorage.clear();
});

type Role = "owner" | "seller" | "accountant";
const served = (code: ServedProfileCode, role: Role = "owner") => ({
  [PROFILE_ROUTE]: json(200, servedProfile(code, role)),
});

async function navLabels(): Promise<(string | null)[]> {
  const nav = await screen.findByRole("navigation", { name: "Navigation principale" });
  return within(nav)
    .getAllByRole("link")
    .map((link) => link.textContent);
}

describe("menus servis selon le profil de la boutique", () => {
  it.each<[ServedProfileCode, Role, string[]]>([
    ["apparel", "owner", ["Accueil", "Ventes", "Stock", "Créances", "Plus"]],
    ["apparel", "accountant", ["Accueil", "Achats", "Stock", "Dépenses", "Inventaire"]],
    ["textile", "seller", ["Accueil", "Nouvelle vente", "Mes ventes", "Créances", "Stock"]],
    ["motos", "owner", ["Accueil", "Ventes", "Stock", "Plus"]],
  ])("%s, %s : barre du bas", async (code, role, labels) => {
    renderApp(SHOP_PATH, { ...memberSession(role), ...served(code, role) });
    expect(await navLabels()).toEqual(labels);
  });

  it("comptable Prêt-à-porter : salutation « Comptable », aucun mot Motos ; axe", async () => {
    const { container } = renderApp(SHOP_PATH, {
      ...memberSession("accountant"),
      ...served("textile", "accountant"),
    });
    expect(await screen.findByText(/— Comptable$/)).toBeVisible();
    for (const motos of ["Camions", "Déplacements", "Chauffeur"]) {
      expect(screen.queryByText(motos)).toBeNull();
    }
    expect(await axeViolations(container)).toEqual([]);
  });

  it("« Inventaire » ouvre l'inventaire de la section Stock", async () => {
    const { router } = renderApp(`${SHOP_PATH}/inventaire`, {
      ...stockRoutes("accountant"),
      ...served("apparel", "accountant"),
    });
    expect(await screen.findByRole("button", { name: "Lancer l'inventaire" })).toBeVisible();
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/stock`);
    expect(router.state.location.search).toBe("?vue=inventaire");
  });
});

describe("Membres : rôles du profil (décision client du 13/11/2026)", () => {
  it.each<[ServedProfileCode, string[]]>([
    ["apparel", ["Propriétaire", "Employé", "Comptable"]],
    ["textile", ["Propriétaire", "Employé", "Comptable"]],
    ["motos", ["Propriétaire", "Vendeur", "Comptable", "Chauffeur"]],
  ])("%s : rôles proposés à l'ajout et libellé des membres", async (code, roles) => {
    renderApp(viewPath("membres"), { ...settingsRoutes("owner"), ...served(code) });
    const list = await screen.findByRole("list", { name: "Membres de la boutique" });
    // Le membre vendeur de la liste porte le libellé du profil (« Vendeur » ou « Employé »).
    expect(within(list).getAllByText(new RegExp(roles[1] ?? "")).length).toBeGreaterThan(0);
    const group = within(screen.getByRole("radiogroup", { name: "Nouveau membre — rôle" }));
    for (const role of roles) expect(group.getByRole("radio", { name: role })).toBeVisible();
    expect(group.getAllByRole("radio")).toHaveLength(roles.length);
    if (code !== "motos") expect(group.queryByRole("radio", { name: "Chauffeur" })).toBeNull();
  });
});
