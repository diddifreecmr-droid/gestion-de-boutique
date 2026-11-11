import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { accountantArticle, ownerArticle } from "../../testing/catalog";
import { json } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import {
  API,
  HAOJUE_ID,
  movement,
  OTHER_ID,
  OWNER_ID,
  STOCK_PAGE,
  stockRoutes,
} from "../../testing/stock";

configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

const SHEET = `${STOCK_PAGE}?vue=mouvements&id=${HAOJUE_ID}`;
const MOVES = `GET ${API}/articles/${HAOJUE_ID}/movements`;
const sale = movement({
  id: "m2",
  type: "sale_out",
  type_label: "Sortie vente",
  quantity: "-1.000",
  balance_after: "1.000",
  author_id: OWNER_ID,
});

function page(items: unknown[], next: string | null = null) {
  return json(200, { article_id: HAOJUE_ID, stock_unit: "UNIT", items, next_cursor: next });
}

describe("fiche stock d'un article (UC-STK-06)", () => {
  it("propriétaire : date, type, lieu, ±quantité, stock après, document, auteur", async () => {
    const members = [{ user_id: OTHER_ID, name: "Paul Comptable" }];
    const { container } = renderApp(
      SHEET,
      stockRoutes("owner", {
        [`GET ${API}/articles/${HAOJUE_ID}`]: json(200, ownerArticle()),
        [`GET ${API}/members`]: json(200, members),
        [MOVES]: page([
          { ...sale, document: { type: "sale", id: "s1", number: "V-000124" } },
          movement(),
        ]),
      }),
    );
    expect(await screen.findByRole("heading", { name: "Haojue HJ125-8" })).toBeVisible();
    const rows = within(screen.getByRole("list", { name: "Mouvements de stock" })).getAllByRole(
      "listitem",
    );
    expect(rows[0]).toHaveTextContent("Sortie vente−1");
    expect(rows[0]).toHaveTextContent("DocumentVente V-000124");
    expect(rows[0]).toHaveTextContent("AuteurAwa Bello");
    expect(rows[1]).toHaveTextContent("Entrée achat+2");
    expect(rows[1]).toHaveTextContent(/Date10\/11\/2026 à 14\sh\s32/);
    expect(rows[1]).toHaveTextContent("LieuGaroua");
    expect(rows[1]).toHaveTextContent("Stock après2");
    expect(rows[1]).toHaveTextContent("DocumentAchat A-000001");
    expect(rows[1]).toHaveTextContent("AuteurPaul Comptable");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("comptable : vente sans numéro (RG-D03), auteur anonyme, « Afficher plus »", async () => {
    const hidden = {
      ...sale,
      author_id: OTHER_ID,
      document: { type: "sale", id: null, number: null },
    };
    const { user, fake } = renderApp(
      SHEET,
      stockRoutes("accountant", {
        [`GET ${API}/articles/${HAOJUE_ID}`]: json(200, accountantArticle()),
        [MOVES]: page([hidden], "c2"),
        [`${MOVES}?cursor=c2`]: page([movement({ id: "m3", condition: "damaged" })]),
      }),
    );
    const list = await screen.findByRole("list", { name: "Mouvements de stock" });
    expect(list).toHaveTextContent("DocumentVente");
    expect(list).not.toHaveTextContent("V-000124");
    expect(list).toHaveTextContent("Auteurun autre membre");
    expect(fake.calls.some((call) => call.url.includes("/members"))).toBe(false);
    await user.click(screen.getByRole("button", { name: "Afficher plus" }));
    expect(await screen.findByText("Garoua (abîmé)")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Afficher plus" })).toBeNull();
  });

  it("le vendeur n'y a pas accès : l'adresse ouvre la matrice, sans appel à l'historique", async () => {
    const { fake } = renderApp(SHEET, stockRoutes("seller"));
    expect(await screen.findByRole("list", { name: "Stock par article" })).toBeVisible();
    expect(fake.calls.some((call) => call.url.includes("/movements"))).toBe(false);
  });
});
