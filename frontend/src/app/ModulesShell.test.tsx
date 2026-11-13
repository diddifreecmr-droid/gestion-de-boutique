/**
 * Modules éteints dans la coquille (décision client du 12/11/2026) : menus servis par le profil
 * (le serveur retire les entrées d'un module éteint), « Plus », adresse directe (« Page
 * introuvable »), refus `MODULE_DISABLED`, lecture hors connexion du profil gardé.
 *
 * L'entrée « Accueil » est servie avec le module `dashboard` (backend `domain/profiles`) : sans
 * ce module, le serveur ne la sert pas et le client ne l'invente pas.
 */
import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { ALL_MODULES, type ModuleCode } from "../core/profile/modules";
import { PROFILE_KEY } from "../core/profile/savedProfiles";
import { axeViolations } from "../testing/axe";
import { apiError, SHOP_A } from "../testing/fakeApi";
import { memberSession, preloadLot1Screens, route, SHOP_PATH } from "../testing/lot1Screens";
import { MINIMAL, profileWith, PROFILE_ROUTE, without } from "../testing/modules";
import { renderApp } from "../testing/renderApp";
import { servedProfile } from "../testing/servedProfile";
import { PROFILE_UNAVAILABLE } from "./ShopShell";

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

const BASIC = [...MINIMAL, "dashboard"];

describe("boutique minimale (socle, journal, catalogue, ventes) et accueil", () => {
  it.each<[Role, string[]]>([
    ["owner", ["Accueil", "Ventes", "Stock", "Plus"]],
    ["seller", ["Accueil", "Nouvelle vente", "Mes ventes", "Stock"]],
    ["accountant", ["Accueil", "Stock"]],
  ])("%s : seules les entrées des modules actifs", async (role, labels) => {
    open(role, BASIC);
    expect(await navLabels()).toEqual(labels);
  });

  it("sans « dashboard » : l'accueil reste (socle, specs § 15.1 « Page d'accueil »)", async () => {
    open("seller", MINIMAL);
    expect(await navLabels()).toEqual(["Accueil", "Nouvelle vente", "Mes ventes", "Stock"]);
  });

  it("chauffeur (Transport à venir) : seul « Mon voyage », son accueil (socle)", async () => {
    open("driver", ALL_MODULES);
    expect(await screen.findByRole("heading", { level: 1 })).toBeVisible();
    expect(await navLabels()).toEqual(["Mon voyage"]);
  });

  it("propriétaire : « Plus » sans Créances, Achats, Dépenses ni Paie ; axe", async () => {
    const { container } = open("owner", BASIC, `${SHOP_PATH}/plus`);
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
    open(role, BASIC, `${SHOP_PATH}/${section}`);
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });
});

describe("un module à la fois", () => {
  it.each<[ModuleCode, Role, string]>([
    ["receivables", "seller", "Créances"],
    ["purchases", "accountant", "Achats"],
    ["expenses", "accountant", "Dépenses"],
  ])("sans %s : %s ne voit plus « %s »", async (module, role, label) => {
    open(role, without(module));
    const labels = await navLabels();
    expect(labels).not.toContain(label);
    expect(labels).toContain("Stock");
  });

  it.each<[Role, string[]]>([
    ["owner", ["Accueil", "Ventes", "Stock", "Plus"]],
    ["accountant", ["Accueil", "Achats", "Stock", "Dépenses"]],
  ])("%s, tous les modules reçus : aucune entrée d'un module à venir", async (role, labels) => {
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
  const offline = { [PROFILE_ROUTE]: new TypeError("Failed to fetch") };

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

  it("hors connexion sans profil gardé : aucun menu deviné, message clair", async () => {
    open("seller", ALL_MODULES, SHOP_PATH, offline);
    expect(await screen.findByText(PROFILE_UNAVAILABLE)).toBeVisible();
    expect(screen.queryByRole("navigation", { name: "Navigation principale" })).toBeNull();
  });

  it("hors connexion : le dernier profil lu est gardé et réutilisé", async () => {
    const saved = servedProfile("motos", "accountant", without("purchases"));
    window.localStorage.setItem(PROFILE_KEY, JSON.stringify({ [SHOP_A]: saved }));
    open("accountant", ALL_MODULES, SHOP_PATH, offline);
    expect(await navLabels()).toEqual(["Accueil", "Stock", "Dépenses"]);
  });

  it("un profil gardé pour un autre rôle n'est pas réutilisé", async () => {
    const saved = servedProfile("motos", "owner");
    window.localStorage.setItem(PROFILE_KEY, JSON.stringify({ [SHOP_A]: saved }));
    open("seller", ALL_MODULES, SHOP_PATH, offline);
    expect(await screen.findByText(PROFILE_UNAVAILABLE)).toBeVisible();
  });

  it("chaque lecture réussie est gardée pour la prochaine ouverture", async () => {
    open("owner", without("receivables"));
    await navLabels();
    const saved = JSON.parse(window.localStorage.getItem(PROFILE_KEY) ?? "{}") as Record<
      string,
      { enabled_modules: string[]; role: string }
    >;
    expect(saved[SHOP_A]?.enabled_modules).toEqual(without("receivables"));
    expect(saved[SHOP_A]?.role).toBe("owner");
  });
});
