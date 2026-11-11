import { act, screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { json, meBody, ROUTES, SHOP_A, tokenBody } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import {
  articleButton,
  plain,
  preloadSales,
  priceField,
  renderSale,
  replaceText,
} from "../../testing/renderSale";
import { OFFLINE_MESSAGE } from "./saleErrorMessage";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
});

const nav = () => screen.getByRole("navigation", { name: "Navigation principale" });

describe("accès à « Nouvelle vente »", () => {
  it("vendeur : depuis la barre du bas et depuis le bouton d'accueil", async () => {
    const { user, router } = renderSale("seller", { path: `/s/${SHOP_A}` });
    await user.click(await screen.findByRole("button", { name: "Nouvelle vente" }));
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/nouvelle-vente`);
    expect(await screen.findByRole("list", { name: "Les plus vendus" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Nouvelle vente" })).toBeVisible();

    await user.click(within(nav()).getByRole("link", { name: "Accueil" }));
    await user.click(within(nav()).getByRole("link", { name: "Nouvelle vente" }));
    expect(within(nav()).getByRole("link", { name: "Nouvelle vente" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(await screen.findByRole("list", { name: "Les plus vendus" })).toBeVisible();
  });

  it("propriétaire : depuis « Ventes »", async () => {
    const { user, router } = renderSale("owner", { path: `/s/${SHOP_A}/ventes` });
    const button = await screen.findByRole("button", { name: "Nouvelle vente" });
    expect(screen.getByRole("heading", { name: "Ventes" })).toBeVisible();
    await user.click(button);
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/nouvelle-vente`);
    expect(await screen.findByRole("list", { name: "Les plus vendus" })).toBeVisible();
  });

  it("comptable : ni « Nouvelle vente » ni « Ventes » n'existent pour lui", async () => {
    const me = meBody({
      shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role: "accountant" }],
    });
    const routes = { [ROUTES.refresh]: json(200, tokenBody("t1")), [ROUTES.me]: json(200, me) };
    renderApp(`/s/${SHOP_A}/nouvelle-vente`, routes);
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });

  it("hors connexion : bannière « Connexion nécessaire », saisie conservée, renvoi d'un appui", async () => {
    const { user, network } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await replaceText(user, priceField(), "770000");
    network.online = false;
    await user.click(screen.getByRole("button", { name: "Valider la vente" }));
    expect(await screen.findByText(OFFLINE_MESSAGE)).toBeVisible();
    expect(screen.getByText("Connexion nécessaire")).toBeVisible();
    expect(plain(priceField().value)).toBe("770 000");

    network.online = true;
    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    await user.click(screen.getByRole("button", { name: "Valider la vente" }));
    expect(
      await screen.findByRole("heading", { name: "Vente enregistrée — reçu n° V-000124" }),
    ).toBeVisible();
    expect(screen.queryByText("Connexion nécessaire")).toBeNull();
  });
});
