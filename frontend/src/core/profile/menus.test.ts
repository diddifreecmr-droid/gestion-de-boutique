import { describe, expect, it } from "vitest";
import { MAX_NAV_ITEMS } from "../../shared/ui";
import { ROLES } from "../auth/me";
import { MOTOS_PROFILE } from "./motos";
import { activeNavKey, findSection, navItems, profileForShop, shopPath } from "./shopProfile";

const SHOP = "01890a5d-ac96-774b-bcce-b302099a8057";
const labels = (role: (typeof ROLES)[number]) => MOTOS_PROFILE.menu(role).map((e) => e.label);

describe("menus par rôle — profil Motos (CDC § 17.4)", () => {
  it.each([
    ["owner", ["Accueil", "Ventes", "Stock", "Camions", "Plus"]],
    ["seller", ["Accueil", "Nouvelle vente", "Mes ventes", "Créances", "Stock"]],
    ["accountant", ["Accueil", "Achats", "Stock", "Déplacements", "Dépenses"]],
    ["driver", ["Mon voyage", "Mes dépenses", "Mes voyages"]],
  ] as const)("%s : entrées exactes", (role, expected) => {
    expect(labels(role)).toEqual(expected);
  });

  it("« Plus » du propriétaire : Créances, Achats, Dépenses, Clients, Paie, Journal, Réglages", () => {
    expect(MOTOS_PROFILE.more("owner").map((e) => e.label)).toEqual([
      "Créances",
      "Achats",
      "Dépenses",
      "Clients",
      "Paie",
      "Journal",
      "Réglages",
    ]);
    for (const role of ["seller", "accountant", "driver"] as const) {
      expect(MOTOS_PROFILE.more(role)).toEqual([]);
    }
  });

  it.each(ROLES)("%s : au plus 5 entrées, clés uniques", (role) => {
    const keys = MOTOS_PROFILE.menu(role).map((e) => e.key);
    expect(keys.length).toBeLessThanOrEqual(MAX_NAV_ITEMS);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("libellés des rôles et profil marqué provisoire", () => {
    expect(ROLES.map((role) => MOTOS_PROFILE.roleLabel(role))).toEqual([
      "Propriétaire",
      "Vendeur",
      "Comptable",
      "Chauffeur",
    ]);
    expect(profileForShop(SHOP)).toBe(MOTOS_PROFILE);
    expect(MOTOS_PROFILE.provisional).toBe(true);
    expect(() => profileForShop("")).toThrow("identifiant de boutique vide");
  });
});

describe("navigation", () => {
  it("traduit le menu en entrées de la barre du bas, l'accueil sur /s/{id}", () => {
    expect(navItems(MOTOS_PROFILE, "seller", SHOP).map((i) => [i.key, i.href])).toEqual([
      ["accueil", `/s/${SHOP}`],
      ["nouvelle-vente", `/s/${SHOP}/nouvelle-vente`],
      ["mes-ventes", `/s/${SHOP}/mes-ventes`],
      ["creances", `/s/${SHOP}/creances`],
      ["stock", `/s/${SHOP}/stock`],
    ]);
    expect(shopPath(SHOP, "stock")).toBe(`/s/${SHOP}/stock`);
  });

  it("entrée active : directe, « Plus » pour ses sous-pages, aucune sinon", () => {
    expect(activeNavKey(MOTOS_PROFILE, "owner", "")).toBe("accueil");
    expect(activeNavKey(MOTOS_PROFILE, "owner", "stock")).toBe("stock");
    expect(activeNavKey(MOTOS_PROFILE, "owner", "journal")).toBe("plus");
    expect(activeNavKey(MOTOS_PROFILE, "seller", "journal")).toBeNull();
    expect(activeNavKey(MOTOS_PROFILE, "seller", "compte")).toBeNull();
  });

  it("une section hors des droits du rôle n'existe pas pour lui", () => {
    expect(findSection(MOTOS_PROFILE, "owner", "paie")?.label).toBe("Paie");
    expect(findSection(MOTOS_PROFILE, "seller", "paie")).toBeNull();
    expect(findSection(MOTOS_PROFILE, "driver", "stock")).toBeNull();
  });
});
