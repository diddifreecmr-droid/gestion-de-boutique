import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { ownerArticle } from "../../testing/catalog";
import { apiError, json } from "../../testing/fakeApi";
import {
  HAOJUE_ID,
  NOW,
  preloadPurchasing,
  purchase,
  PURCHASES_PATH,
  purchasingRoutes,
  route,
  setClock,
  supplier,
  withArticleSearch,
} from "../../testing/purchasing";
import { chooseArticle, fillLine, lineGroup, sent } from "../../testing/purchasingUi";
import { renderApp } from "../../testing/renderApp";
import { plain } from "../../testing/renderSale";
import { OFFLINE_MESSAGE } from "./purchaseErrors";

const NEW_PATH = `${PURCHASES_PATH}?vue=nouvel`;
const POST = route("POST", "/purchases");
const GAP = apiError(422, "PRICE_GAP_CONFIRMATION_REQUIRED", "Prix très différent", {
  lines: [{ line: 0, article_id: HAOJUE_ID, last_cost: 520000, unit_price: 52000 }],
});

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

async function oneLine(routes: Parameters<typeof purchasingRoutes>[1]) {
  const view = renderApp(NEW_PATH, withArticleSearch(purchasingRoutes("accountant", routes)));
  await screen.findByRole("heading", { name: "Nouvel achat" });
  await chooseArticle(view.user, "hao", "Haojue HJ125-8");
  await fillLine(view.user, "20", "52000");
  return view;
}

describe("écart de prix de plus de 30 % (UC-ACH-01)", () => {
  it("confirmation explicite, puis renvoi de la même saisie avec confirm_price_gap", async () => {
    const { user, fake } = await oneLine({ [POST]: [GAP, json(201, purchase())] });
    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Prix très différent du dernier achat",
    });
    expect(plain(dialog.textContent)).toContain(
      "Le dernier achat était à 520 000 FCFA. Confirmer 52 000 FCFA ?",
    );
    await user.click(within(dialog).getByRole("button", { name: "Confirmer le prix" }));
    await screen.findByRole("heading", { name: "Achat enregistré — A-000012" });
    const first = sent(fake.calls, "POST", "/purchases", 0) as { id: string };
    const second = sent(fake.calls, "POST", "/purchases", 1) as { id: string };
    expect(first).toMatchObject({ confirm_price_gap: false });
    expect(second).toMatchObject({ id: first.id, confirm_price_gap: true });
  });

  it("« Corriger le prix » ferme la confirmation sans rien envoyer de plus", async () => {
    const { user, fake } = await oneLine({ [POST]: GAP });
    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Corriger le prix" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(fake.count(POST)).toBe(1);
    expect(within(lineGroup(1)).getByLabelText("Prix unitaire")).toBeVisible();
  });

  it("coupure réseau : rien n'est enregistré, la saisie reste", async () => {
    const { user } = await oneLine({ [POST]: new TypeError("Failed to fetch") });
    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    expect(await screen.findByText(OFFLINE_MESSAGE)).toBeVisible();
    expect(within(lineGroup(1)).getByLabelText("Quantité")).toHaveValue("20");
  });
});

describe("sans quitter l'écran : fournisseur et article", () => {
  it("fournisseur : actifs proposés, création rapide par le nom", async () => {
    const created = supplier({ id: "sup-new", name: "Garoua Motos SARL", city: null });
    const { user, fake } = await oneLine({
      [route("POST", "/suppliers")]: json(201, created),
      [POST]: json(201, purchase()),
    });
    const field = screen.getByLabelText("Fournisseur (facultatif)");
    await user.type(field, "an");
    expect(screen.queryByRole("list", { name: "Fournisseurs proposés" })).toBeNull();
    await user.clear(field);
    await user.type(field, "Garoua Motos SARL");
    await user.click(
      screen.getByRole("button", { name: "Nouveau fournisseur « Garoua Motos SARL »" }),
    );
    expect(await screen.findByText("Garoua Motos SARL")).toBeVisible();
    expect(sent(fake.calls, "POST", "/suppliers")).toMatchObject({ name: "Garoua Motos SARL" });
    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    await screen.findByRole("heading", { name: "Achat enregistré — A-000012" });
    expect(sent(fake.calls, "POST", "/purchases")).toMatchObject({ supplier_id: "sup-new" });
  });

  it("fournisseur existant choisi ; doublon refusé avec un message clair", async () => {
    const { user } = await oneLine({
      [route("POST", "/suppliers")]: apiError(409, "DUPLICATE", "Nom déjà pris"),
    });
    const field = screen.getByLabelText("Fournisseur (facultatif)");
    await user.type(field, "Haojue D");
    await user.click(screen.getByRole("button", { name: "Nouveau fournisseur « Haojue D »" }));
    expect(
      await screen.findByText("Un fournisseur porte déjà ce nom : choisissez-le dans la liste."),
    ).toBeVisible();
    const proposed = screen.getByRole("list", { name: "Fournisseurs proposés" });
    await user.click(within(proposed).getByRole("button", { name: /Haojue Douala/ }));
    expect(screen.getByRole("button", { name: "Changer de fournisseur" })).toBeVisible();
  });

  it("article introuvable : « Créer l'article » ouvre le formulaire du catalogue dans le flux", async () => {
    const suzuki = ownerArticle({
      id: "art-suzuki",
      display_name: "Suzuki AX100",
      stock_unit: "UNIT",
    });
    const { user, fake, container } = renderApp(
      NEW_PATH,
      withArticleSearch(
        purchasingRoutes("accountant", { [route("POST", "/articles")]: json(201, suzuki) }),
      ),
    );
    await screen.findByRole("heading", { name: "Nouvel achat" });
    const line = lineGroup(1);
    await user.type(within(line).getByLabelText("Article"), "suz");
    expect(await within(line).findByText("Aucun article ne correspond à « suz ».")).toBeVisible();
    await user.click(within(line).getByRole("button", { name: "Créer l'article" }));
    const form = await within(line).findByRole("form", { name: "Nouvel article" });
    await user.type(within(form).getByLabelText(/^Marque/), "Suzuki");
    await user.type(within(form).getByLabelText(/^Modèle/), "AX100");
    expect(within(form).queryByLabelText(/Prix de base/)).toBeNull();
    await user.click(within(form).getByRole("button", { name: "Créer l'article" }));
    expect(await within(line).findByText("Suzuki AX100")).toBeVisible();
    expect(sent(fake.calls, "POST", "/articles")).toMatchObject({ fields: { brand: "Suzuki" } });
    expect(container.innerHTML).not.toContain("Nouvel article</h2>");
  });
});
