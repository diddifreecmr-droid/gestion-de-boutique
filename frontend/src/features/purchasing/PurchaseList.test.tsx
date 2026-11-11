import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import { json } from "../../testing/fakeApi";
import {
  HAOJUE_ID,
  NOW,
  page,
  preloadPurchasing,
  purchase,
  PURCHASE_ID,
  PURCHASES_PATH,
  purchasingRoutes,
  route,
  setClock,
  withArticleSearch,
} from "../../testing/purchasing";
import { renderApp } from "../../testing/renderApp";
import { money } from "../../testing/renderSale";

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const SECOND = purchase({
  id: "p-2",
  number: "A-000011",
  supplier_id: null,
  location_id: "loc-garoua",
  article_count: 3,
  total: 900000,
  paid: 400000,
  payment_status: "partially_paid",
});
const ITEMS = [
  purchase(),
  SECOND,
  purchase({ id: "p-3", number: "A-000010", total: 50000, paid: 50000, payment_status: "paid" }),
  purchase({ id: "p-4", number: "A-000009", supplier_id: "sup-2", status: "cancelled" }),
];

const first = async () => {
  const [row] = within(await list()).getAllByRole("link");
  if (row === undefined) throw new Error("liste vide");
  return row;
};
const list = () => screen.findByRole("list", { name: "Liste des achats" });

describe("liste des achats (UC-ACH-05)", () => {
  it("mois en cours, totaux de la période, lignes et statuts de paiement", async () => {
    const { container } = renderApp(
      PURCHASES_PATH,
      purchasingRoutes("accountant", { [route("GET", "/purchases")]: json(200, page(ITEMS)) }),
    );
    const rows = within(await list()).getAllByRole("link");
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent(
      `Haojue Douala A-00001211/11/2026 · Garoua-Boulaï · 1 article${money(10800000)}À payer`,
    );
    expect(rows[1]).toHaveTextContent(`Sans fournisseur A-000011`);
    expect(rows[1]).toHaveTextContent("Garoua · 3 articles");
    expect(rows[1]).toHaveTextContent("Payé en partie");
    expect(rows[2]).toHaveTextContent("Payé");
    expect(rows[3]).toHaveTextContent("Ancien Import");
    expect(rows[3]).toHaveTextContent("Annulé");
    expect(screen.getByText("Total des achats du 01/11/2026 au 30/11/2026")).toBeVisible();
    expect(screen.getByText(/^3 achats · marchandise/)).toBeVisible();
    expect(screen.getByRole("radio", { name: "Ce mois-ci" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("« Afficher plus » ajoute la page suivante ; une ligne ouvre la fiche", async () => {
    const { user, router } = renderApp(
      PURCHASES_PATH,
      purchasingRoutes("owner", {
        [route("GET", "/purchases")]: json(200, page([purchase()], { next_cursor: "c2" })),
        [route("GET", "/purchases?cursor=c2")]: json(200, page([SECOND])),
        [route("GET", `/purchases/${PURCHASE_ID}`)]: json(200, purchase()),
      }),
    );
    await list();
    await user.click(screen.getByRole("button", { name: "Afficher plus" }));
    expect(await within(await list()).findByText("A-000011")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Afficher plus" })).toBeNull();
    await user.click(await first());
    expect(router.state.location.search).toBe(`?vue=fiche&id=${PURCHASE_ID}`);
    expect(await screen.findByRole("heading", { name: "Achat A-000012" })).toBeVisible();
  });

  it("filtres : période, fournisseur, article, lieu", async () => {
    const empty = json(200, page([]));
    const { user, fake } = renderApp(
      PURCHASES_PATH,
      withArticleSearch(
        purchasingRoutes("accountant", {
          [route("GET", "/purchases?from=2026-11-05&to=2026-11-11")]: empty,
          [route("GET", "/purchases?from=2026-11-05&to=2026-11-11&supplier_id=sup-1")]: empty,
          [route(
            "GET",
            `/purchases?from=2026-11-05&to=2026-11-11&supplier_id=sup-1&article_id=${HAOJUE_ID}`,
          )]: empty,
          [route(
            "GET",
            `/purchases?from=2026-11-05&to=2026-11-11&supplier_id=sup-1&location_id=loc-gb&article_id=${HAOJUE_ID}`,
          )]: empty,
        }),
      ),
    );
    expect(await screen.findByText("Aucun achat sur cette période.")).toBeVisible();
    await user.click(screen.getByRole("radio", { name: "7 derniers jours" }));
    await user.click(screen.getByRole("button", { name: "Filtres" }));
    await user.click(screen.getByRole("radio", { name: "Haojue Douala" }));
    await user.type(screen.getByLabelText("Article"), "hao");
    const found = await screen.findByRole("list", { name: "Articles à filtrer" });
    await user.click(within(found).getByRole("button", { name: "Haojue HJ125-8" }));
    await user.click(screen.getByRole("radio", { name: "Garoua-Boulaï" }));
    await screen.findByText("Aucun achat sur cette période.");
    const urls = fake.calls.filter((c) => c.url.includes("/purchases")).map((c) => c.url);
    expect(urls.at(-1)).toContain("location_id=loc-gb");
    await user.click(screen.getByRole("radio", { name: "Autres dates" }));
    await user.clear(screen.getByLabelText("Du"));
    await user.type(screen.getByLabelText("Du"), "2026-11-20");
    expect(screen.getByText("La date de début est après la date de fin")).toBeVisible();
  });
});
