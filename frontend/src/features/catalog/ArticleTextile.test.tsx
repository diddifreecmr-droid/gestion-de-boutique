import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { API, catalogRoutes, HAOJUE_ID, ownerArticle } from "../../testing/catalog";
import { json, SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { money, replaceText } from "../../testing/renderSale";
import { servedProfile } from "../../testing/servedProfile";

const NEW = `/s/${SHOP_A}/stock?article=nouveau`;
const SHEET = `/s/${SHOP_A}/stock?article=${HAOJUE_ID}`;
const POST = `POST ${API}/articles`;
const GET = `GET ${API}/articles/${HAOJUE_ID}`;
const PUT = `PUT ${API}/articles/${HAOJUE_ID}/prices`;
const PROFILE = `GET ${API}/profile`;

configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

/** WX « Wax Fleur de mariage » (recette Lot 3) : mètre, vendu à la pièce de 5,49 m. */
const wax = (overrides: Parameters<typeof ownerArticle>[0] = {}) =>
  ownerArticle({
    display_name: "Wax Fleur de mariage",
    brand: null,
    model: null,
    stock_unit: "METER",
    sold_by_piece: true,
    piece_length_m: "5.49",
    attributes: {},
    base_price: 2500,
    min_price: null,
    base_price_piece: 13000,
    min_price_piece: null,
    ...overrides,
  });

function input(label: string): HTMLInputElement {
  const field = screen.getByLabelText(label);
  if (!(field instanceof HTMLInputElement)) throw new Error(`« ${label} » n'est pas un champ`);
  return field;
}

const textile = (extra = {}) =>
  catalogRoutes("owner", { [PROFILE]: json(200, servedProfile("textile", "owner")), ...extra });

describe("fiche article Textile (T39)", () => {
  it("création : unité Mètre / Pièce, vente à la pièce, longueur exigée, prix au mètre et à la pièce", async () => {
    const { user, fake, container } = renderApp(
      NEW,
      textile({ [POST]: json(201, wax()), [GET]: json(200, wax()) }),
    );
    const unit = await screen.findByRole("radiogroup", { name: "Unité" });
    expect(
      within(unit)
        .getAllByRole("radio")
        .map((r) => r.textContent),
    ).toEqual(["Mètre", "Pièce"]);
    expect(screen.queryByRole("radiogroup", { name: "Vente à la pièce" })).toBeNull();
    await user.type(input("Nom"), "Wax Fleur de mariage");
    await user.click(within(unit).getByRole("radio", { name: "Mètre" }));
    expect(input("Prix au mètre (facultatif)")).toBeVisible();
    const byPiece = screen.getByRole("radiogroup", { name: "Vente à la pièce" });
    await user.click(within(byPiece).getByRole("radio", { name: "Oui" }));
    expect(input("Prix à la pièce (facultatif)")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(
      screen.getByText("Longueur de la pièce : obligatoire pour la vente à la pièce"),
    ).toBeVisible();
    expect(fake.count(POST)).toBe(0);
    await user.type(input("Longueur de la pièce (m)"), "5,49");
    await replaceText(user, input("Prix au mètre (facultatif)"), "2500");
    await replaceText(user, input("Prix à la pièce (facultatif)"), "13000");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(await screen.findByText("Article créé : Wax Fleur de mariage")).toBeVisible();
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === POST)?.body).toMatchObject({
      fields: {
        name: "Wax Fleur de mariage",
        unit: "METER",
        sold_by_piece: true,
        piece_length_m: "5.49",
      },
      base_price: 2500,
      base_price_piece: 13000,
    });
  });

  it("unité Pièce : ni vente à la pièce ni longueur, le prix de base est « à la pièce »", async () => {
    const { user, fake } = renderApp(
      NEW,
      textile({ [POST]: json(201, wax()), [GET]: json(200, wax()) }),
    );
    const unit = await screen.findByRole("radiogroup", { name: "Unité" });
    await user.click(within(unit).getByRole("radio", { name: "Mètre" }));
    await user.click(screen.getByRole("radio", { name: "Oui" }));
    await user.type(input("Longueur de la pièce (m)"), "5,49");
    await user.click(within(unit).getByRole("radio", { name: "Pièce" }));
    expect(screen.queryByRole("radiogroup", { name: "Vente à la pièce" })).toBeNull();
    expect(screen.queryByLabelText("Longueur de la pièce (m)")).toBeNull();
    expect(input("Prix à la pièce (facultatif)")).toBeVisible();
    await user.type(input("Nom"), "Bazin riche");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    await screen.findByText(/Article créé/);
    const body = fake.calls.find((c) => `${c.method} ${c.url}` === POST)?.body as {
      fields: Record<string, unknown>;
    };
    expect(body.fields).toEqual({ name: "Bazin riche", unit: "PIECE" });
    expect("base_price_piece" in body).toBe(false);
  });

  it("fiche : unité « Mètre », prix au mètre et à la pièce ; les deux se modifient", async () => {
    const { user, fake } = renderApp(
      SHEET,
      textile({ [GET]: json(200, wax()), [PUT]: json(200, wax({ base_price_piece: 12500 })) }),
    );
    const details = await screen.findByRole("region", { name: "Détails" });
    expect(within(details).getByText("Mètre")).toBeVisible();
    const prices = screen.getByRole("region", { name: "Prix de vente" });
    expect(within(prices).getByText("Prix au mètre")).toBeVisible();
    expect(within(prices).getByText(money(2500))).toBeVisible();
    expect(within(prices).getByText("Prix à la pièce")).toBeVisible();
    expect(within(prices).getByText(money(13000))).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Modifier les prix" }));
    await replaceText(user, input("Prix à la pièce"), "12500");
    await user.click(screen.getByRole("button", { name: "Enregistrer les prix" }));
    await screen.findByText("Prix enregistrés");
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === PUT)?.body).toMatchObject({
      base_price: 2500,
      base_price_piece: 12500,
    });
  });
});

describe("garde-fou du nom à la création (VOC-04)", () => {
  const apparel = (extra = {}) =>
    catalogRoutes("owner", { [PROFILE]: json(200, servedProfile("apparel", "owner")), ...extra });
  const robe = ownerArticle({ display_name: "Robe Bleu Marine", brand: null, model: null });

  it("« Robe Bleu Marine Robe » : avertissement avant l'envoi, nom proposé utilisable", async () => {
    const { user, fake } = renderApp(
      NEW,
      apparel({ [POST]: json(201, robe), [GET]: json(200, robe) }),
    );
    await user.type(await screen.findByLabelText("Nom"), "Robe Bleu Marine Robe");
    expect(input("Marque")).not.toBeVisible(); // facultative, sous « Plus de détails »
    expect(input("Marque")).toHaveAttribute("aria-required", "false");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(screen.getByText(/Mot répété dans le nom « Robe Bleu Marine Robe »/)).toBeVisible();
    expect(fake.count(POST)).toBe(0);
    await user.click(screen.getByRole("button", { name: "Utiliser « Robe Bleu Marine »" }));
    expect(input("Nom").value).toBe("Robe Bleu Marine");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    await screen.findByText("Article créé : Robe Bleu Marine");
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === POST)?.body).toMatchObject({
      fields: { name: "Robe Bleu Marine" },
    });
  });

  it("second appui : le nom est gardé tel quel", async () => {
    const { user, fake } = renderApp(
      NEW,
      apparel({ [POST]: json(201, robe), [GET]: json(200, robe) }),
    );
    await user.type(await screen.findByLabelText("Nom"), "Robe Robe");
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    expect(fake.count(POST)).toBe(0);
    await user.click(screen.getByRole("button", { name: "Créer l'article" }));
    await screen.findByText(/Article créé/);
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === POST)?.body).toMatchObject({
      fields: { name: "Robe Robe" },
    });
  });
});
