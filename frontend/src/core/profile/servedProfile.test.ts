/** T37 — profil servi par `GET /profile` : menus, libellés et rôles des 3 profils. */
import { describe, expect, it } from "vitest";
import { MAX_NAV_ITEMS } from "../../shared/ui";
import type { Role } from "../auth/me";
import { servedProfile } from "../../testing/servedProfile";
import type { ServedProfileCode } from "../../testing/profileMenus";
import { profileFromResponse } from "./servedProfile";

const profile = (code: ServedProfileCode, role: Role) =>
  profileFromResponse(servedProfile(code, role), role);
const labels = (code: ServedProfileCode, role: Role) =>
  profile(code, role).menu.map((e) => e.label);
const moreLabels = (code: ServedProfileCode, role: Role) =>
  profile(code, role).more.map((e) => e.label);

describe("menus servis par rôle (modules disponibles à l'ouverture)", () => {
  it.each<[ServedProfileCode, Role, string[]]>([
    // Motos : Camions (transport, à venir) et Déplacements (transfers) ne sont pas servis.
    ["motos", "owner", ["Accueil", "Ventes", "Stock", "Plus"]],
    ["motos", "seller", ["Accueil", "Nouvelle vente", "Mes ventes", "Créances", "Stock"]],
    ["motos", "accountant", ["Accueil", "Achats", "Stock", "Dépenses"]],
    ["motos", "driver", ["Mon voyage"]],
    ["apparel", "owner", ["Accueil", "Ventes", "Stock", "Créances", "Plus"]],
    ["apparel", "seller", ["Accueil", "Nouvelle vente", "Mes ventes", "Créances", "Stock"]],
    ["apparel", "accountant", ["Accueil", "Achats", "Stock", "Dépenses", "Inventaire"]],
    ["textile", "owner", ["Accueil", "Ventes", "Stock", "Créances", "Plus"]],
    ["textile", "accountant", ["Accueil", "Achats", "Stock", "Dépenses", "Inventaire"]],
  ])("%s, %s : entrées exactes", (code, role, expected) => {
    expect(labels(code, role)).toEqual(expected);
  });

  it("« Plus » du propriétaire : Motos sans Paie, Prêt-à-porter sans Créances (déjà en bas)", () => {
    expect(moreLabels("motos", "owner")).toEqual([
      "Créances",
      "Achats",
      "Dépenses",
      "Clients",
      "Journal",
      "Réglages",
    ]);
    const apparel = ["Achats", "Dépenses", "Clients", "Journal", "Réglages"];
    expect(moreLabels("apparel", "owner")).toEqual(apparel);
    expect(moreLabels("textile", "owner")).toEqual(apparel);
    expect(moreLabels("apparel", "seller")).toEqual([]);
  });

  it("codes servis → segments d'URL du client ; au plus 5 entrées, clés uniques", () => {
    expect(profile("apparel", "owner").menu.map((e) => [e.code, e.key])).toEqual([
      ["home", ""],
      ["sales", "ventes"],
      ["stock", "stock"],
      ["receivables", "creances"],
      ["more", "plus"],
    ]);
    expect(profile("apparel", "accountant").menu.at(-1)?.key).toBe("inventaire");
    for (const code of ["motos", "apparel", "textile"] as const) {
      for (const role of ["owner", "seller", "accountant"] as const) {
        const keys = profile(code, role).menu.map((e) => e.key);
        expect(keys.length).toBeLessThanOrEqual(MAX_NAV_ITEMS);
        expect(new Set(keys).size).toBe(keys.length);
      }
    }
  });
});

describe("rôles et libellés du profil", () => {
  it.each<[ServedProfileCode, string[]]>([
    ["motos", ["Propriétaire", "Vendeur", "Comptable", "Chauffeur"]],
    ["apparel", ["Propriétaire", "Employé", "Comptable"]],
    ["textile", ["Propriétaire", "Employé", "Comptable"]],
  ])("%s : rôles proposés", (code, expected) => {
    const served = profile(code, "owner");
    expect(served.roles.map((choice) => choice.label)).toEqual(expected);
    expect(served.roleLabel("seller")).toBe(expected[1]);
  });

  it("hors Motos, pas de Chauffeur : son libellé est une erreur explicite", () => {
    expect(() => profile("apparel", "owner").roleLabel("driver")).toThrow(
      "Rôle « driver » absent du profil « apparel »",
    );
  });

  it("champs d'article et de vente exposés tels que servis", () => {
    const textile = profile("textile", "seller");
    expect(textile.articleFields.map((f) => f.code)).toContain("piece_length_m");
    expect(textile.saleFields.map((f) => f.label)).toEqual(["Longueur (m)"]);
    expect(textile.stockUnits).toEqual(["METER", "PIECE"]);
    expect(profile("apparel", "seller").saleFields.map((f) => f.label)).toEqual([
      "Taille",
      "Couleur",
    ]);
  });
});

describe("rupture de contrat : erreur explicite (fail-fast)", () => {
  const body = () => servedProfile("motos", "seller");

  it("code de menu inconnu", () => {
    const served = body();
    served.menu = [{ code: "lottery", label: "Loterie", module: "sales", children: [] }];
    expect(() => profileFromResponse(served, "seller")).toThrow(
      "Code de menu inconnu reçu de l'API : « lottery »",
    );
  });

  it("module inconnu, rôle inconnu, menu servi pour un autre rôle", () => {
    const badModule = body();
    badModule.menu = [{ code: "stock", label: "Stock", module: "casino", children: [] }];
    expect(() => profileFromResponse(badModule, "seller")).toThrow("Module inconnu");
    const badRole = body();
    badRole.roles = [...badRole.roles, { code: "cashier", label: "Caissier" }];
    expect(() => profileFromResponse(badRole, "seller")).toThrow("Rôle inconnu");
    expect(() => profileFromResponse(body(), "owner")).toThrow(
      "Profil servi pour le rôle « seller », attendu « owner »",
    );
  });

  it("sous-entrées ailleurs que sous « Plus »", () => {
    const served = body();
    const child = { code: "audit", label: "Journal", module: "audit", children: [] };
    served.menu = [{ code: "stock", label: "Stock", module: "catalog", children: [child] }];
    expect(() => profileFromResponse(served, "seller")).toThrow("seule l'entrée « Plus »");
  });
});
