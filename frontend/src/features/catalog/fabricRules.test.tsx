import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { stockPolicyOf } from "../../core/gateways/catalogArticle";
import { countText, pieceWords } from "../../core/profile/pieceWords";
import { axeViolations } from "../../testing/axe";
import { API } from "../../testing/catalog";
import { json } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { servedProfile } from "../../testing/servedProfile";
import { COLUMNS, matrixUrl, STOCK_PAGE, stockRoutes, stockRow } from "../../testing/stock";
import { rollsText } from "../stock/quantities";
import { NO_PRICES } from "./createPrices";
import { addColors, createBody, patchBody, settingsErrors, splitColors } from "./fabricDraft";
import { colorOf, groupByFabric } from "./fabricGroups";

configure({ asyncUtilTimeout: 5000 });
beforeEach(() => {
  window.localStorage.clear();
});

const ROULEAU = pieceWords("rouleau");

describe("vocabulaire du rouleau et règles des tissus", () => {
  it("le mot servi se décline ; un mot inconnu échoue", () => {
    expect([ROULEAU.perTitle, ROULEAU.of, countText(7, ROULEAU), countText(1, ROULEAU)]).toEqual([
      "Au rouleau",
      "du rouleau",
      "7 rouleaux",
      "1 rouleau",
    ]);
    expect(pieceWords("pièce").perTitle).toBe("À la pièce");
    expect(() => pieceWords("ballot")).toThrow("Mot de la pièce inconnu");
    expect(rollsText({ count: 7, rest: "12.0" }, "METER", ROULEAU)).toMatch(
      /^7 rouleaux \+ 12\sm$/,
    );
    expect(rollsText({ count: 1, rest: "0.0" }, "METER", ROULEAU)).toBe("1 rouleau");
  });

  it("couleurs : saisie rapide sans doublon ; corps de création et de modification", () => {
    expect(splitColors(" rouge ;bleu ciel\nVert,, ")).toEqual(["Rouge", "Bleu ciel", "Vert"]);
    expect(addColors(["Rouge"], "rouge, Jaune")).toEqual(["Rouge", "Jaune"]);
    const settings = { rollLength: "25,5", meterOnly: false, threshold: "", prices: NO_PRICES };
    expect(settingsErrors({ ...settings, rollLength: "" }).rollLength).toMatch(/longueur/);
    expect(settingsErrors({ ...settings, rollLength: "0" }).rollLength).toMatch(/mètres/);
    expect(settingsErrors({ ...settings, meterOnly: true, rollLength: "" })).toEqual({});
    const accountant = { setPrices: false, minPriceEnabled: true };
    expect(createBody(" Wax ", ["Rouge"], settings, accountant)).toEqual({
      fabric: "Wax",
      colors: ["Rouge"],
      roll_length_m: "25.5",
      meter_only: false,
      alert_threshold: null,
    });
    const owner = { setPrices: true, minPriceEnabled: false };
    expect(patchBody({ ...settings, meterOnly: true }, owner)).toEqual({
      roll_length_m: null,
      meter_only: true,
      alert_threshold: null,
      prices: { base_price: null, base_price_piece: null },
    });
  });

  it("groupes par tissu dans l'ordre servi ; couleur lue sur l'article", () => {
    const groups = groupByFabric([
      { fabric: "Djampar", id: 1 },
      { fabric: null, id: 2 },
      { fabric: "Djampar", id: 3 },
    ]);
    expect(groups.map((g) => [g.fabric, g.items.map((i) => i.id)])).toEqual([
      ["Djampar", [1, 3]],
      [null, [2]],
    ]);
    expect(colorOf({ display_name: "Djampar — Bleu nuit", attributes: {} })).toBe("Bleu nuit");
    expect(() => colorOf({ display_name: "Fil", attributes: {} })).toThrow("couleur");
  });

  it("stock caché au seul employé d'un profil « stock réservé au gérant »", () => {
    expect(stockPolicyOf(servedProfile("textile", "seller"))).toEqual({
      hidden: true,
      sellsWithoutStock: true,
    });
    expect(stockPolicyOf(servedProfile("textile", "owner")).hidden).toBe(false);
    expect(stockPolicyOf(servedProfile("motos", "seller"))).toEqual({
      hidden: false,
      sellsWithoutStock: false,
    });
  });
});

describe("stock du gérant Textile : rouleaux et tissus", () => {
  it("« 7 rouleaux + 12 m », lignes rangées sous leur tissu ; axe", async () => {
    const row = (id: string, name: string, rolls: number, rest: string) =>
      stockRow("owner", {
        article_id: id,
        display_name: name,
        stock_unit: "METER",
        total: "222.0",
        rolls,
        meters_rest: rest,
      });
    const body = {
      locations: COLUMNS,
      items: [
        row("a1", "Djampar — Rouge", 7, "12.0"),
        row("a2", "Djampar — Bleu", 2, "0.0"),
        stockRow("owner", { article_id: "a3", display_name: "Fil noir" }),
      ],
    };
    const { container } = renderApp(
      STOCK_PAGE,
      stockRoutes("owner", {
        [`GET ${API}/profile`]: json(200, servedProfile("textile", "owner")),
        [matrixUrl()]: json(200, body),
      }),
    );
    const djampar = await screen.findByRole("list", { name: "Stock du tissu Djampar" });
    expect(within(djampar).getByText("7 rouleaux + 12 m")).toBeVisible();
    expect(within(djampar).getByText("2 rouleaux")).toBeVisible();
    expect(within(screen.getByRole("list", { name: "Autres articles" })).getByText("Fil noir"));
    expect(await axeViolations(container)).toEqual([]);
  });
});
