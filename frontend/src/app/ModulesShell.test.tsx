/**
 * Modules éteints dans la coquille (décision client du 12/11/2026) : menus, « Plus », adresse
 * directe (« Page introuvable »), refus `MODULE_DISABLED`, lecture hors connexion.
 */
import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { ALL_MODULES, type ModuleCode } from "../core/profile/modules";
import { MODULES_KEY } from "../core/profile/useShopModules";
import { axeViolations } from "../testing/axe";
import { apiError, SHOP_A } from "../testing/fakeApi";
import { memberSession, preloadLot1Screens, route, SHOP_PATH } from "../testing/lot1Screens";
import { MINIMAL, profileWith, PROFILE_ROUTE, without } from "../testing/modules";
import { renderApp } from "../testing/renderApp";

beforeAll(preloadLot1Screens);

type Role = "owner" | "seller" | "accountant" | "driver";

function open(role: Role, modules: readonly string[], path = SHOP_PATH, extra = {}) {
  return renderApp(path, { ...memberSession(role), ...profileWith(modules), ...extra });
}

async function navLabels(): Promise<(string | null)[]> {
  const nav = await screen.findByRole("navigation", { name: "Navigation principale" });
  return within(nav)
    .getAllByRole("link")
    .map((link) => link.textContent);
}

describe("boutique minimale (socle, journal, catalogue, ventes)", () => {
  it.each<[Role, string[]]>([
    ["owner", ["Accueil", "Ventes", "Stock", "Plus"]],
    ["seller", ["Accueil", "Nouvelle vente", "Mes ventes", "Stock"]],
    ["accountant", ["Accueil", "Stock"]],
    ["driver", ["Mon voyage"]],
  ])("%s : seules les entrées des modules toujours actifs", async (role, labels) => {
    open(role, MINIMAL);
    expect(await navLabels()).toEqual(labels);
  });

  it("propriétaire : « Plus » sans Créances, Achats, Dépenses ni Paie ; axe", async () => {
    const { container } = open("owner", MINIMAL, `${SHOP_PATH}/plus`);
    expect(await screen.findByRole("heading", { name: "Plus" })).toBeVisible();
    const tiles = screen.getAllByRole("button").map((b) => b.textContent);
    expect(tiles).toEqual(expect.arrayContaining(["Clients", "Journal", "Réglages"]));
    for (const gone of ["Créances", "Achats", "Dépenses", "Paie", "Mon compte"]) {
      expect(within(screen.getByRole("main")).queryByRole("button", { name: gone })).toBeNull();
    }
    expect(await axeViolations(container)).toEqual([]);
  });

  it.each<[Role, string]>([
    ["owner", "creances"],
    ["owner", "achats"],
    ["owner", "depenses"],
    ["owner", "camions"],
    ["owner", "paie"],
    ["seller", "creances"],
    ["accountant", "deplacements"],
    ["driver", "mes-voyages"],
    ["driver", "mes-depenses"],
  ])("%s : l'adresse directe /%s donne « Page introuvable »", async (role, section) => {
    open(role, MINIMAL, `${SHOP_PATH}/${section}`);
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });
});

describe("un module à la fois", () => {
  it.each<[ModuleCode, Role, string]>([
    ["receivables", "seller", "Créances"],
    ["purchases", "accountant", "Achats"],
    ["expenses", "accountant", "Dépenses"],
    ["transfers", "accountant", "Déplacements"],
    ["transport", "owner", "Camions"],
  ])("sans %s : %s ne voit plus « %s »", async (module, role, label) => {
    open(role, without(module));
    const labels = await navLabels();
    expect(labels).not.toContain(label);
    expect(labels).toContain("Stock");
  });

  it("chauffeur sans Transport : seulement son accueil", async () => {
    open("driver", without("transport"));
    expect(await navLabels()).toEqual(["Mon voyage"]);
  });

  it("tous les modules reçus, à venir compris : aucune entrée d'un module à venir", async () => {
    open("owner", ALL_MODULES);
    expect(await navLabels()).toEqual(["Accueil", "Ventes", "Stock", "Plus"]);
  });

  it.each<[Role, string[]]>([
    ["accountant", ["Accueil", "Achats", "Stock", "Dépenses"]],
    ["driver", ["Mon voyage"]],
  ])("%s, tous les modules reçus : ni Déplacements, ni Mes voyages", async (role, labels) => {
    const { container } = open(role, ALL_MODULES);
    expect(await navLabels()).toEqual(labels);
    expect(screen.queryByText(/Disponible au Lot|arrive bientôt/)).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("propriétaire, tous les modules reçus : « Plus » sans Paie ni Mon compte", async () => {
    open("owner", ALL_MODULES, `${SHOP_PATH}/plus`);
    expect(await screen.findByRole("heading", { name: "Plus" })).toBeVisible();
    for (const gone of ["Paie", "Mon compte"]) {
      expect(within(screen.getByRole("main")).queryByRole("button", { name: gone })).toBeNull();
    }
  });
});

describe("refus du serveur et hors connexion", () => {
  it("403 MODULE_DISABLED à l'ouverture d'un écran : message clair, la coquille reste", async () => {
    open("owner", ALL_MODULES, `${SHOP_PATH}/clients`, {
      [route("GET", "/customers")]: apiError(403, "MODULE_DISABLED", "Module désactivé"),
    });
    expect(
      await screen.findByText("Cette fonction n'est pas activée pour cette boutique."),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Retour à l'accueil" })).toBeVisible();
    expect(await navLabels()).toContain("Plus");
  });

  it("hors connexion sans modules gardés : seulement les modules toujours actifs", async () => {
    open("seller", ALL_MODULES, SHOP_PATH, {
      [PROFILE_ROUTE]: new TypeError("Failed to fetch"),
    });
    expect(await navLabels()).toEqual(["Accueil", "Nouvelle vente", "Mes ventes", "Stock"]);
  });

  it("hors connexion : les derniers modules lus sont gardés et réutilisés", async () => {
    window.localStorage.setItem(MODULES_KEY, JSON.stringify({ [SHOP_A]: without("purchases") }));
    open("accountant", ALL_MODULES, SHOP_PATH, {
      [PROFILE_ROUTE]: new TypeError("Failed to fetch"),
    });
    expect(await navLabels()).toEqual(["Accueil", "Stock", "Dépenses"]);
  });

  it("chaque lecture réussie est gardée pour la prochaine ouverture", async () => {
    open("owner", without("receivables"));
    await navLabels();
    const saved = JSON.parse(window.localStorage.getItem(MODULES_KEY) ?? "{}") as Record<
      string,
      string[]
    >;
    expect(saved[SHOP_A]).toEqual(without("receivables"));
  });
});
