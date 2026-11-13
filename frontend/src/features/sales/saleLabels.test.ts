import { describe, expect, it } from "vitest";
import type { CatalogArticle, PaymentMode } from "../../core/gateways/catalogContract";
import { sellableFirst } from "./articleOrder";
import { articleTitle } from "./articleTitle";
import { defaultPayment, groupModes } from "./paymentChoices";
import { articleSearchHint, saleSearchLabel, searchesChassis } from "./profileLabels";

const mode = (id: string, name: string, order: number): PaymentMode => ({
  id,
  name,
  reference_required: false,
  active: true,
  display_order: order,
  version: 1,
});

const article = (id: string, available: string, saleMode: "unit" | "meter" = "unit") =>
  ({
    id,
    name: id,
    sale_mode: saleMode,
    unit_label: "unité",
    base_price: null,
    min_price: null,
    available,
  }) satisfies CatalogArticle;

describe("titre d'un article (audit UX du 13/11/2026)", () => {
  it.each([
    ["Robe Bleu Marine Robe", "Robe Bleu Marine"],
    ["Robe Robe Bleu", "Robe Bleu"],
    ["Bleu Marine Robe robe", "Bleu Marine Robe"],
    ["Pagne Wax Hollandais Pagne Wax", "Pagne Wax Hollandais"],
    ["  Haojue   HJ125-8 ", "Haojue HJ125-8"],
    ["Tissu Wax Super Wax", "Tissu Wax Super Wax"],
    ["Robe", "Robe"],
    ["Été Robe ete", "Été Robe"],
  ])("« %s » → « %s »", (name, title) => {
    expect(articleTitle(name)).toBe(title);
  });

  it("refuse un nom vide", () => {
    expect(() => articleTitle("  ")).toThrow("Article sans nom");
  });
});

describe("libellés selon le profil", () => {
  it("Motos : marque ou modèle", () => {
    const fields = [
      { code: "brand", label: "Marque" },
      { code: "model", label: "Modèle" },
      { code: "engine_cc", label: "Cylindrée (cm³)" },
    ];
    expect(articleSearchHint(fields)).toBe("Cherchez par marque ou modèle");
  });

  it("Prêt-à-porter : les champs du profil, jamais « modèle »", () => {
    const fields = [
      { code: "name", label: "Nom" },
      { code: "reference", label: "Référence" },
      { code: "type", label: "Type" },
      { code: "brand", label: "Marque" },
    ];
    expect(articleSearchHint(fields)).toBe("Cherchez par nom, référence ou marque");
  });

  it("sans champ cherchable : « nom ou référence »", () => {
    expect(articleSearchHint([])).toBe("Cherchez par nom ou référence");
  });

  it("le châssis seulement si le profil le saisit", () => {
    expect(searchesChassis(["color", "chassis_number"])).toBe(true);
    expect(searchesChassis(["size", "color"])).toBe(false);
    expect(saleSearchLabel(true)).toBe("Chercher un n° de vente ou de châssis");
    expect(saleSearchLabel(false)).toBe("Chercher un n° de vente");
  });
});

describe("modes de paiement visibles", () => {
  const modes = [
    mode("om", "Orange Money", 1),
    mode("cash", "Espèces", 2),
    mode("mtn", "MTN MoMo", 3),
    mode("vir", "Virement", 4),
    mode("chq", "Chèque", 5),
  ];

  it("Espèces d'abord et par défaut, puis les 2 premiers autres ; le reste derrière « Autre mode »", () => {
    const { visible, hidden } = groupModes(modes);
    expect(visible.map((m) => m.id)).toEqual(["cash", "om", "mtn"]);
    expect(hidden.map((m) => m.id)).toEqual(["vir", "chq"]);
    expect(defaultPayment(modes)).toBe("cash");
  });

  it("sans « Espèces » : les 3 premiers, le premier par défaut", () => {
    const others = modes.filter((m) => m.id !== "cash");
    expect(groupModes(others).visible.map((m) => m.id)).toEqual(["om", "mtn", "vir"]);
    expect(defaultPayment(others)).toBe("om");
  });

  it("aucun mode actif : erreur explicite", () => {
    expect(() => defaultPayment([])).toThrow("aucun mode de paiement actif");
  });
});

describe("ordre des articles proposés", () => {
  it("les ruptures et les articles au mètre après ceux en stock, ordre gardé", () => {
    const items = [
      article("a", "0"),
      article("b", "3"),
      article("c", "2.5", "meter"),
      article("d", "1.000"),
    ];
    expect(sellableFirst(items).map((a) => a.id)).toEqual(["b", "d", "a", "c"]);
  });
});
