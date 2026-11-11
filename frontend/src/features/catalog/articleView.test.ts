import { describe, expect, expectTypeOf, it } from "vitest";
import { accountantArticle, ownerArticle } from "../../testing/catalog";
import {
  articleView,
  costsOf,
  pricesOf,
  type AccountantArticle,
  type SellerArticle,
} from "./articleView";
import { catalogRights, catalogRole } from "./catalogRights";

describe("vue d'un article selon le rôle (TR-05)", () => {
  it("propriétaire : prix, coûts, historique ; valeurs du profil réunies", () => {
    const view = articleView("owner", ownerArticle({ price_history: [] }));
    expect(view.kind).toBe("owner");
    expect(pricesOf(view)).toMatchObject({ basePrice: 780000, minPrice: 720000 });
    expect(costsOf(view)).toEqual({ lastCost: 650000, wac: null });
    expect(view.values).toMatchObject({ brand: "Haojue", model: "HJ125-8", engine_cc: 125 });
    expect(view.kind === "owner" && view.history).toEqual([]);
  });

  it("vendeur : aucun coût dans la vue, même si le serveur en envoyait (défense en profondeur)", () => {
    const view = articleView("seller", ownerArticle());
    expect(view).not.toHaveProperty("costs");
    expect(JSON.stringify(view)).not.toMatch(/650000|last_cost|lastCost|wac/);
    expect(costsOf(view)).toBeNull();
    expect(pricesOf(view)?.basePrice).toBe(780000);
  });

  it("types : le vendeur n'a pas de champ de coût, le comptable pas de prix", () => {
    expectTypeOf<SellerArticle>().not.toHaveProperty("costs");
    expectTypeOf<SellerArticle>().not.toHaveProperty("history");
    expectTypeOf<AccountantArticle>().not.toHaveProperty("prices");
  });

  it("comptable : coûts, aucun prix de vente même si le serveur en envoyait", () => {
    const view = articleView("accountant", ownerArticle());
    expect(view).not.toHaveProperty("prices");
    expect(JSON.stringify(view)).not.toContain("780000");
    expect(pricesOf(view)).toBeNull();
    expect(costsOf(articleView("accountant", accountantArticle()))?.lastCost).toBe(650000);
  });

  it("contrat rompu ou rôle sans accès : erreur explicite", () => {
    expect(() => articleView("owner", accountantArticle())).toThrow("« base_price » absent");
    expect(() => articleView("accountant", accountantArticle({ wac: "1" as never }))).toThrow(
      "« wac » absent",
    );
    expect(() => articleView("driver", ownerArticle())).toThrow("chauffeur");
    expect(() => articleView("owner", ownerArticle({ status: "deleted" }))).toThrow("inconnu");
    expect(() => catalogRole("seller")).toThrow("gestion du catalogue");
    expect(catalogRights(catalogRole("accountant"))).toEqual({
      edit: true,
      setPrices: false,
      archive: false,
    });
  });
});
