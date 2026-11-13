import { describe, expect, it } from "vitest";
import type { Role } from "../auth/me";
import { servedProfile } from "../../testing/servedProfile";
import { ALL_MODULES, shopModules } from "./modules";
import { profileFromResponse } from "./servedProfile";
import {
  activeNavKey,
  findSection,
  homeEntry,
  navItems,
  shopPath,
  withModules,
} from "./shopProfile";

const SHOP = "01890a5d-ac96-774b-bcce-b302099a8057";
const motos = (role: Role) => profileFromResponse(servedProfile("motos", role), role);

describe("navigation", () => {
  it("traduit le menu en entrées de la barre du bas, l'accueil sur /s/{id}", () => {
    expect(navItems(motos("seller"), SHOP).map((i) => [i.key, i.href])).toEqual([
      ["accueil", `/s/${SHOP}`],
      ["nouvelle-vente", `/s/${SHOP}/nouvelle-vente`],
      ["mes-ventes", `/s/${SHOP}/mes-ventes`],
      ["creances", `/s/${SHOP}/creances`],
      ["stock", `/s/${SHOP}/stock`],
    ]);
    expect(shopPath(SHOP, "stock")).toBe(`/s/${SHOP}/stock`);
    expect(homeEntry(motos("seller"))?.label).toBe("Accueil");
  });

  it("entrée active : directe, « Plus » pour ses sous-pages, aucune sinon", () => {
    expect(activeNavKey(motos("owner"), "")).toBe("accueil");
    expect(activeNavKey(motos("owner"), "stock")).toBe("stock");
    expect(activeNavKey(motos("owner"), "journal")).toBe("plus");
    expect(activeNavKey(motos("seller"), "journal")).toBeNull();
    expect(activeNavKey(motos("seller"), "compte")).toBeNull();
  });

  it("une section hors du menu de l'acteur n'existe pas pour lui", () => {
    expect(findSection(motos("owner"), "journal")?.label).toBe("Journal");
    expect(findSection(motos("seller"), "journal")).toBeNull();
    expect(findSection(motos("owner"), "paie")).toBeNull();
  });
});

describe("filtre par modules (profil gardé hors connexion)", () => {
  it("une entrée d'un module éteint disparaît ; « Plus » vide disparaît", () => {
    const owner = motos("owner");
    const minimal = withModules(owner, shopModules([]));
    expect(minimal.more.map((e) => e.label)).toEqual(["Clients", "Journal", "Réglages"]);
    expect(minimal.menu.map((e) => e.label)).toEqual(["Accueil", "Ventes", "Stock", "Plus"]);
    // Seule « Créances » (receivables, éteint) dans « Plus » : « Plus » disparaît.
    const noMore = withModules({ ...owner, more: owner.more.slice(0, 1) }, shopModules([]));
    expect(noMore.menu.map((e) => e.key)).not.toContain("plus");
  });

  it("modules à venir reçus : jamais d'entrée Camions, Paie ou Déplacements", () => {
    const all = withModules(motos("owner"), shopModules(ALL_MODULES));
    const labels = [...all.menu, ...all.more].map((e) => e.label);
    for (const gone of ["Camions", "Paie", "Déplacements"]) expect(labels).not.toContain(gone);
  });
});
