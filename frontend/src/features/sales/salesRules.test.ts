import { describe, expect, it } from "vitest";
import { capturedAtHeader } from "../../core/api/capturedAt";
import { ApiError, NetworkError } from "../../core/api/errors";
import { saleModeOf, toCatalogArticle, unitWord } from "../../core/gateways/httpCatalog";
import { duplicate, paymentIncomplete } from "../../core/gateways/saleErrors";
import type { SaleSetup } from "../../core/gateways/catalogContract";
import { ownerArticle } from "../../testing/catalog";
import { customerKind } from "./buildCommand";
import { actionErrorMessage, saleErrorMessage } from "./saleErrorMessage";
import { locationChoice, NO_POINT_OF_SALE, NO_USUAL_LOCATION } from "./saleLocation";
import { ownerCosts } from "./saleView";
import { warningText } from "./warningText";

const GAROUA = { id: "g", name: "Garoua" };
const NGAOUNDERE = { id: "n", name: "Ngaoundéré" };
const setup = (overrides: Partial<SaleSetup> = {}): SaleSetup => ({
  locations: [GAROUA, NGAOUNDERE],
  default_location_id: "n",
  payment_modes: [],
  ...overrides,
});

describe("lieu de la vente (Q-36)", () => {
  it("vendeur : son lieu habituel seulement, sinon un message", () => {
    expect(locationChoice(setup(), "seller")).toEqual({
      status: "ready",
      choices: [NGAOUNDERE],
      initial: NGAOUNDERE,
    });
    expect(locationChoice(setup({ default_location_id: null }), "seller")).toEqual({
      status: "none",
      message: NO_USUAL_LOCATION,
    });
  });

  it("propriétaire : tous les points de vente, présélection du lieu habituel ou du premier", () => {
    expect(locationChoice(setup(), "owner")).toMatchObject({ initial: NGAOUNDERE });
    expect(locationChoice(setup({ default_location_id: null }), "owner")).toMatchObject({
      choices: [GAROUA, NGAOUNDERE],
      initial: GAROUA,
    });
    expect(locationChoice(setup({ locations: [] }), "owner")).toEqual({
      status: "none",
      message: NO_POINT_OF_SALE,
    });
  });
});

describe("passerelle réelle du catalogue : assemblage article + stock", () => {
  it("prix, minimum actif, stock du lieu ; 0 sans ligne de stock ; jamais de coût", () => {
    const row = {
      article_id: "a",
      display_name: "x",
      stock_unit: "UNIT",
      cells: [{ location_id: "g", sellable: "3.000", damaged: "0.000" }],
      incoming: "0",
      total: "3",
      stock_status: "ok" as const,
      alert_threshold: "2",
    };
    const article = ownerArticle({ id: "a", stock_unit: "UNIT" });
    const view = toCatalogArticle(article, row, "g", "moto");
    expect(view).toEqual({
      id: "a",
      name: "Haojue HJ125-8",
      sale_mode: "unit",
      unit_label: "moto",
      base_price: 780_000,
      min_price: 720_000,
      available: "3.000",
    });
    expect(
      toCatalogArticle({ ...article, min_price_active: false }, undefined, "g", "u"),
    ).toMatchObject({ min_price: null, available: "0" });
    expect(() => toCatalogArticle(article, row, "autre", "u")).toThrow("colonne « autre » absente");
    expect(saleModeOf("METER")).toBe("meter");
    expect(() => saleModeOf("KG")).toThrow("Unité de stock inconnue");
    expect(unitWord("motos")).toBe("moto");
    expect(unitWord("textile")).toBe("unité");
  });
});

describe("contrat et messages", () => {
  it("X-Captured-At : ISO 8601 avec le décalage du fuseau de l'appareil", () => {
    expect(capturedAtHeader(new Date("2026-11-11T09:05:07.042Z"))).toMatch(
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}$/,
    );
    const back = new Date(capturedAtHeader(new Date("2026-11-11T09:05:07.042Z")));
    expect(back.toISOString()).toBe("2026-11-11T09:05:07.042Z");
    expect(() => capturedAtHeader(new Date("x"))).toThrow("instant invalide");
  });

  it("nouveaux refus du serveur dits en clair", () => {
    const at = (code: string, details = {}) =>
      saleErrorMessage(new ApiError(422, code, "m", details), [], "Garoua");
    expect(at("PAYMENT_INCOMPLETE", { total: 10, paid: 4, remaining: 6 })).toMatch(
      /il manque 6\sFCFA/,
    );
    expect(at("LOCATION_NOT_ALLOWED")).toMatch(/lieu de vente habituel/);
    expect(at("LOCATION_NOT_POINT_OF_SALE")).toMatch(/^Garoua n'est plus un point de vente/);
    expect(at("DUPLICATE", { field: "chassis_number", value: "LBX1", sale_number: null })).toBe(
      "Le numéro de châssis LBX1 est saisi deux fois dans cette vente.",
    );
    expect(() => paymentIncomplete(new ApiError(422, "PAYMENT_INCOMPLETE", "m", {}))).toThrow(
      "total",
    );
    expect(() =>
      duplicate(new ApiError(409, "DUPLICATE", "m", { field: "f", value: "v", sale_number: 3 })),
    ).toThrow("sale_number");
  });

  it("actions sur une vente : réseau, droits, refus ; le reste est relancé", () => {
    expect(actionErrorMessage(new NetworkError("x"), "Annulation")).toMatch(
      /^Connexion nécessaire/,
    );
    expect(actionErrorMessage(new ApiError(403, "FORBIDDEN", "m"), "Annulation")).toMatch(/droit/);
    expect(
      actionErrorMessage(new ApiError(409, "VERSION_CONFLICT", "Déjà modifiée"), "Annulation"),
    ).toBe("Annulation refusé : Déjà modifiée (VERSION_CONFLICT).");
    const bug = new TypeError("bug");
    expect(() => actionErrorMessage(bug, "x")).toThrow(bug);
  });

  it("avertissement de plafond, type de client et coûts du propriétaire : fail-fast", () => {
    const warning = { code: "CREDIT_LIMIT_EXCEEDED", message: "m", details: { limit: 1 } };
    expect(() => warningText(warning)).toThrow("due_after");
    expect(warningText({ code: "AUTRE", message: "Texte", details: {} })).toBe("Texte");
    expect(customerKind("company")).toBe("company");
    expect(() => customerKind("ngo")).toThrow("Type de client inconnu");
    const line = {
      article_id: "a",
      article_name: "Haojue",
      sale_mode: "unit",
      quantity: "1",
      stock_quantity: "1",
      stock_unit: "UNIT",
      base_price: 1,
      unit_price: 1,
      line_total: 1,
      details: [],
    };
    expect(ownerCosts("seller", line)).toBeNull();
    expect(() => ownerCosts("owner", line)).toThrow("sans coûts figés");
  });
});
