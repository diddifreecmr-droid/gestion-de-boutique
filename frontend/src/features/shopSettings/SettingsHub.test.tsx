import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { renderApp } from "../../testing/renderApp";
import { json } from "../../testing/fakeApi";
import {
  MODES,
  preloadSettings,
  route,
  SETTINGS_PATH,
  settingsRoutes,
  viewPath,
} from "../../testing/shopSettingsApi";

beforeAll(preloadSettings);
beforeEach(() => {
  window.localStorage.clear();
});

describe("Réglages de la boutique — sommaire et droits (CDC § 4.2, E3)", () => {
  it("propriétaire : quatre écrans et « Mon compte », sans violation axe", async () => {
    const { user, router, container } = renderApp(SETTINGS_PATH, settingsRoutes("owner"));
    expect(await screen.findByRole("heading", { name: "Réglages" })).toBeVisible();
    const list = screen.getByRole("list", { name: "Réglages de la boutique" });
    const titles = within(list)
      .getAllByRole("button")
      .map((button) => button.querySelector(".text-lead")?.textContent);
    expect(titles).toEqual(["Membres", "Lieux", "Modes de paiement", "Réglages de la boutique"]);
    expect(await axeViolations(container)).toEqual([]);

    await user.click(within(list).getByRole("button", { name: /^Membres/ }));
    expect(router.state.location.search).toBe("?vue=membres");
    expect(await screen.findByRole("heading", { name: "Membres" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Retour aux réglages" }));
    expect(router.state.location.search).toBe("");

    await user.click(within(screen.getByRole("list", { name: "Mon compte" })).getByRole("button"));
    expect(router.state.location.pathname).toMatch(/\/compte$/);
  });

  it.each(["seller", "accountant", "driver"] as const)(
    "%s : la section n'existe pas (rien n'apparaît sans le droit)",
    async (role) => {
      const { fake } = renderApp(viewPath("membres"), settingsRoutes(role));
      expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
      expect(fake.count(route("GET", "/members"))).toBe(0);
    },
  );

  it("coupure réseau : « Connexion nécessaire » puis « Réessayer » relit l'écran", async () => {
    const modes = route("GET", "/payment-modes");
    const { user, fake } = renderApp(viewPath("modes"), {
      ...settingsRoutes("owner"),
      [modes]: [new TypeError("Failed to fetch"), json(200, MODES)],
    });
    expect(await screen.findByText("Connexion nécessaire pour ouvrir les réglages.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("list", { name: "Modes de paiement" })).toBeVisible();
    expect(fake.count(modes)).toBe(2);
  });
});
