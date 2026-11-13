import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { attachment, pdfFile, UPLOAD } from "../../testing/attachments";
import { axeViolations } from "../../testing/axe";
import {
  accountantArticle,
  API,
  catalogRoutes,
  HAOJUE_ID,
  ownerArticle,
} from "../../testing/catalog";
import { apiError, json, SHOP_A, type Reply } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { replaceText } from "../../testing/renderSale";
import { servedProfile } from "../../testing/servedProfile";

configure({ asyncUtilTimeout: 5000 });
beforeEach(() => {
  window.localStorage.clear();
});

const SHEET = `/s/${SHOP_A}/stock?article=${HAOJUE_ID}`;
const ADJUST = `POST ${API}/adjustments`;
type Role = "owner" | "accountant";

const WAX = {
  display_name: "Wax Fleur de mariage",
  brand: null,
  model: null,
  stock_unit: "METER",
  sold_by_piece: true,
  piece_length_m: "5.49",
  attributes: {},
} as const;

function stock(sellable: string) {
  return {
    locations: [
      { location_id: "loc-boutique", name: "Boutique", kind: "shop", is_point_of_sale: true },
    ],
    items: [
      {
        article_id: HAOJUE_ID,
        display_name: WAX.display_name,
        stock_unit: "METER",
        cells: [{ location_id: "loc-boutique", sellable, damaged: "0.0" }],
        incoming: "0.0",
        total: sellable,
        stock_status: "ok",
        alert_threshold: "1.0",
      },
    ],
  };
}

function renderSheet(role: Role, extra: Record<string, Reply> = {}, article: object = WAX) {
  const body = role === "owner" ? ownerArticle(article) : accountantArticle(article);
  const base = catalogRoutes(role, {
    [`GET ${API}/profile`]: json(200, servedProfile("textile", role)),
    [`GET ${API}/articles/${HAOJUE_ID}`]: json(200, body),
    ...extra,
  });
  // `GET /stock?q=…&sort=name` : une réponse neuve à chaque lecture.
  const routes = new Proxy(base, {
    get: (target, key) =>
      typeof key === "string" && key.startsWith(`GET ${API}/stock?`)
        ? json(200, stock("54.9"))
        : (Reflect.get(target, key) as unknown),
  });
  return renderApp(SHEET, routes);
}

const lengthField = () => screen.getByLabelText("Longueur de la chute");
const adjusted = { id: "adj-1", article_id: HAOJUE_ID, balance_after: "54.5" };

describe("« Déclarer une chute » sur la fiche Textile (T41, RG-X06, UC-TEX-03)", () => {
  it("propriétaire : 0,4 m, note, photo → ajustement Chute en sortie ; confirmation, toast ; axe", async () => {
    const { user, fake, container } = renderSheet("owner", {
      [ADJUST]: json(201, adjusted),
      [UPLOAD]: json(201, attachment({ owner_type: "stock_adjustment", owner_id: null })),
    });
    await user.click(await screen.findByRole("button", { name: "Déclarer une chute" }));
    const form = within(await screen.findByRole("region", { name: "Déclarer une chute" }));
    expect(form.getByText(/Stock vendable à Boutique : 54,9\sm/)).toBeVisible();
    await user.type(lengthField(), "0,45");
    expect(form.getByText("Une décimale au plus (ex. 2,5)")).toBeVisible();
    await replaceText(user, lengthField() as HTMLInputElement, "60");
    expect(form.getByText(/La chute dépasse le stock : 54,9\sm à Boutique/)).toBeVisible();
    await replaceText(user, lengthField() as HTMLInputElement, "0,4");
    await user.type(form.getByLabelText("Note (facultative)"), "Bout abîmé");
    await user.upload(form.getByLabelText("Photo de la chute (facultative)"), pdfFile());
    expect(await form.findByText("Pièce enregistrée.")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);

    await user.click(form.getByRole("button", { name: "Enregistrer la chute" }));
    const dialog = within(await screen.findByRole("dialog"));
    expect(dialog.getByText(/Déclarer une chute de 0,4\sm \?/)).toBeVisible();
    expect(fake.count(ADJUST)).toBe(0);
    await user.click(dialog.getByRole("button", { name: "Déclarer la chute" }));
    expect(await screen.findByText(/Chute de 0,4\sm enregistrée/)).toBeVisible();
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === ADJUST)?.body).toMatchObject({
      location_id: "loc-boutique",
      article_id: HAOJUE_ID,
      direction: "out",
      reason: "offcut",
      condition: "sellable",
      quantity: "0.4",
      note: "Bout abîmé",
      photo_id: attachment().id,
    });
    expect(screen.getByRole("button", { name: "Déclarer une chute" })).toBeVisible();
  });

  it("comptable : déclare aussi ; aucun coût montré ; refus du serveur dit en clair", async () => {
    const { user } = renderSheet("accountant", {
      [ADJUST]: apiError(403, "FORBIDDEN", "Interdit"),
    });
    await user.click(await screen.findByRole("button", { name: "Déclarer une chute" }));
    await user.type(lengthField(), "0,4");
    await user.click(screen.getByRole("button", { name: "Enregistrer la chute" }));
    await user.click(await screen.findByRole("button", { name: "Déclarer la chute" }));
    expect(
      await screen.findByText("Vous n'avez pas le droit de faire cette action."),
    ).toBeVisible();
    expect(screen.queryByText(/prix de base|coût/i)).toBeNull();
  });

  it("longueur vide : erreur au premier appui, rien n'est envoyé ; Annuler revient à la fiche", async () => {
    const { user, fake } = renderSheet("owner");
    await user.click(await screen.findByRole("button", { name: "Déclarer une chute" }));
    await user.click(await screen.findByRole("button", { name: "Enregistrer la chute" }));
    expect(screen.getByText("Indiquez la longueur")).toBeVisible();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(fake.count(ADJUST)).toBe(0);
    await user.click(screen.getByRole("button", { name: "Annuler" }));
    expect(screen.getByRole("button", { name: "Déclarer une chute" })).toBeVisible();
  });

  it.each([
    ["à la pièce (stock en pièces)", { ...WAX, stock_unit: "PIECE", sold_by_piece: false }],
    ["archivé", { ...WAX, status: "archived" }],
  ])("article %s : pas de « Déclarer une chute »", async (_case, article) => {
    renderSheet("owner", {}, article);
    expect(await screen.findByRole("heading", { name: WAX.display_name })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Déclarer une chute" })).toBeNull();
  });
});
