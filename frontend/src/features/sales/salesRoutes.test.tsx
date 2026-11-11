import { act, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { articleButton, plain, priceField, replaceText } from "../../testing/renderSale";
import { OFFLINE_MESSAGE } from "./saleErrorMessage";

function signedIn(role: "seller" | "owner" | "accountant"): Record<string, Reply | Reply[]> {
  const me = meBody({ shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }] });
  return { [ROUTES.refresh]: json(200, tokenBody("t1")), [ROUTES.me]: json(200, me) };
}

beforeEach(() => {
  window.localStorage.clear();
});

const nav = () => screen.getByRole("navigation", { name: "Navigation principale" });

describe("accès à « Nouvelle vente »", () => {
  it("vendeur : depuis la barre du bas et depuis le bouton d'accueil", async () => {
    const { user, router } = renderApp(`/s/${SHOP_A}`, signedIn("seller"));
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
    const { user, router } = renderApp(`/s/${SHOP_A}/ventes`, signedIn("owner"));
    expect(await screen.findByRole("heading", { name: "Ventes" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Nouvelle vente" }));
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/nouvelle-vente`);
    expect(await screen.findByRole("list", { name: "Les plus vendus" })).toBeVisible();
  });

  it("comptable : l'écran n'existe pas pour lui", async () => {
    renderApp(`/s/${SHOP_A}/nouvelle-vente`, signedIn("accountant"));
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });

  it("hors connexion : bannière « Connexion nécessaire », saisie conservée, renvoi d'un appui", async () => {
    const { user } = renderApp(`/s/${SHOP_A}/nouvelle-vente`, signedIn("seller"));
    await user.click(await articleButton("Haojue HJ125-8"));
    await replaceText(user, priceField(), "770000");
    act(() => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByText("Connexion nécessaire")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Valider la vente" }));
    expect(await screen.findByText(OFFLINE_MESSAGE)).toBeVisible();
    expect(plain(priceField().value)).toBe("770 000");

    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.queryByText("Connexion nécessaire")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Valider la vente" }));
    expect(
      await screen.findByRole("heading", { name: "Vente enregistrée — reçu n° V-000124" }),
    ).toBeVisible();
  });
});
