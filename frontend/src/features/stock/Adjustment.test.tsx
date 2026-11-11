import { configure, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { axeViolations } from "../../testing/axe";
import { ownerArticle } from "../../testing/catalog";
import { apiError, json } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { API, GAROUA, HAOJUE_ID, STOCK_PAGE, stockRoutes } from "../../testing/stock";

configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

const POST = `POST ${API}/adjustments`;
const FORM = `${STOCK_PAGE}?vue=ajustement&id=${HAOJUE_ID}`;
const done = {
  id: "a1",
  location_id: GAROUA,
  article_id: HAOJUE_ID,
  direction: "out",
  quantity: "1",
  condition: "sellable",
  reason: "other",
  note: "Moto prêtée",
  photo_id: null,
  inventory_id: null,
  created_at: "2026-11-10T10:00:00Z",
  author_id: "u",
  balance_after: "0.000",
};
const afterRoutes = {
  [`GET ${API}/articles/${HAOJUE_ID}`]: json(200, ownerArticle()),
  [`GET ${API}/members`]: json(200, []),
  [`GET ${API}/articles/${HAOJUE_ID}/movements`]: json(200, {
    article_id: HAOJUE_ID,
    stock_unit: "UNIT",
    items: [],
    next_cursor: null,
  }),
};

describe("ajustement ponctuel (UC-STK-08)", () => {
  it("« Autre » exige une note ; photo désactivée avec sa raison", async () => {
    const { user, fake, container } = renderApp(FORM, stockRoutes("owner"));
    expect(await screen.findByRole("heading", { name: "Ajustement de stock" })).toBeVisible();
    expect(await screen.findByText("Haojue HJ125-8")).toBeVisible();
    expect(screen.getByText("Stock vendable ici : 1 — abîmé : 0")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    expect(screen.getByText("Pièces jointes : à venir")).toBeVisible();
    expect(screen.getByRole("button", { name: "Ajouter une photo" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await user.type(screen.getByLabelText("Quantité"), "1");
    await user.click(screen.getByRole("radio", { name: "Autre" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer l'ajustement" }));
    expect(await screen.findByText(/la note est obligatoire pour « Autre »/)).toBeVisible();
    expect(fake.count(POST)).toBe(0);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("envoi idempotent (id UUIDv7), message avec le stock après, puis l'historique", async () => {
    const { user, fake, router } = renderApp(
      FORM,
      stockRoutes("owner", { [POST]: json(201, done), ...afterRoutes }),
    );
    await user.type(await screen.findByLabelText("Quantité"), "1");
    await user.click(screen.getByRole("radio", { name: "Autre" }));
    await user.type(screen.getByLabelText("Note"), "Moto prêtée");
    await user.click(screen.getByRole("button", { name: "Enregistrer l'ajustement" }));
    expect(await screen.findByText("Ajustement enregistré — stock après : 0")).toBeVisible();
    const body = fake.calls.find((call) => `${call.method} ${call.url}` === POST)?.body as Record<
      string,
      unknown
    >;
    expect(body).toMatchObject({
      location_id: GAROUA,
      article_id: HAOJUE_ID,
      direction: "out",
      quantity: "1",
      condition: "sellable",
      reason: "other",
      note: "Moto prêtée",
    });
    expect(isUuidV7(String(body["id"]))).toBe(true);
    expect(router.state.location.search).toBe(`?vue=mouvements&id=${HAOJUE_ID}`);
  });

  it("stock insuffisant : message avec le disponible et les autres lieux", async () => {
    const refusal = apiError(422, "STOCK_INSUFFICIENT", "Stock insuffisant dans ce lieu", {
      available: "1",
      requested: "3",
      other_locations: [{ location_id: "n", location_name: "Ngaoundéré", available: "2" }],
    });
    const { user } = renderApp(FORM, stockRoutes("accountant", { [POST]: refusal }));
    await user.type(await screen.findByLabelText("Quantité"), "3");
    await user.click(screen.getByRole("radio", { name: "Casse" }));
    await user.click(screen.getByRole("button", { name: "Enregistrer l'ajustement" }));
    expect(
      await screen.findByText(
        "Stock insuffisant : 1 disponible à Garoua. Autres lieux — Ngaoundéré : 2.",
      ),
    ).toBeVisible();
  });

  it("sans article choisi : le demande ; la recherche propose les articles dès la 1re lettre", async () => {
    const { user, fake } = renderApp(`${STOCK_PAGE}?vue=ajustement`, stockRoutes("owner"));
    await user.click(await screen.findByRole("button", { name: "Enregistrer l'ajustement" }));
    expect(await screen.findByText("Choisissez l'article")).toBeVisible();
    expect(screen.getByText("Choisissez le motif")).toBeVisible();
    await user.type(screen.getByLabelText("Article"), "y");
    await user.click(await screen.findByRole("button", { name: "Yamaha Crypton" }));
    await user.type(screen.getByLabelText("Quantité"), "1,5");
    await user.click(screen.getByRole("button", { name: "Enregistrer l'ajustement" }));
    expect(await screen.findByText("Cet article se compte en nombre entier")).toBeVisible();
    expect(fake.count(POST)).toBe(0);
  });
});
